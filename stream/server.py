# -*- coding: utf-8 -*-
"""
server.py
USB 웹캠 영상에 YOLO 탐지 결과(bbox+라벨)를 입혀 WebSocket으로
실시간 스트리밍하는 서버. Jetson Nano 등 LAN 안의 보드에서 직접 돌리고,
같은 네트워크의 브라우저가 http://<host>:<port>/ 로 접속해서 본다.

사용법:
    python stream/server.py
    python stream/server.py --source 0 --width 480 --height 360 --max-fps 5
    python stream/server.py --model weights/best.pt --device 0

동작 방식:
    카메라 읽기 + 추론은 블로킹 작업이라 별도 스레드(capture_loop)에서 돌리고,
    가장 최근 프레임 1장만 FrameBroadcaster에 보관한다. 클라이언트별로
    프레임을 큐에 쌓지 않으므로, 느린 클라이언트나 느린 보드에서도
    지연이 계속 누적되지 않고 항상 최신 프레임으로 건너뛴다.
"""

import argparse
import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from detector import infer_and_annotate, load_model

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = REPO_ROOT / "weights" / "best.pt"
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_COMBOS = Path(__file__).resolve().parent / "combos.json"
DEFAULT_TIMINGS = Path(__file__).resolve().parent / "timing.json"
DEFAULT_DOSAGE = Path(__file__).resolve().parent / "dosage.json"

# 감지가 한두 프레임 안 잡혀도 배너/타이밍 안내가 바로 꺼지지 않게 유지하는
# 시간(초). 탐지가 프레임마다 깜빡이는 것 때문에 화면이 같이 깜빡이는 걸
# 완화한다.
DETECTION_HOLD_SECS = 1.5


def _load_json_rules(path: Path, label: str):
    """stream/combos.json, stream/timing.json 공용 로더.

    파일이 없거나 비어 있어도 에러 없이 빈 값을 돌려주고, 그 경우 해당
    기능은 꺼진 채로 나머지 스트리밍은 정상 동작한다.
    """
    if not path.exists():
        print(f"[stream] {label} 파일 없음({path}) — 해당 기능 비활성화")
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"[stream] {label} 로드: {path}")
    return data


def load_combo_rules(path: Path):
    return _load_json_rules(path, "combos") or []


def load_timing_rules(path: Path):
    return _load_json_rules(path, "timing") or {}


def load_dosage_rules(path: Path):
    return _load_json_rules(path, "dosage") or {}


def match_combo(detected_classes, rules):
    """현재 감지된 클래스 집합에 맞는 조합 규칙을 찾는다.

    규칙의 "classes"가 detected_classes의 부분집합이면 매칭된 것으로 본다.
    caution 규칙이 하나라도 매칭되면 그걸 우선 반환한다(경고를 good 배너에
    가려서 안 보이게 하지 않기 위함). caution이 없으면 먼저 매칭된 good
    규칙을 반환한다.
    """
    detected = set(detected_classes)
    first_good = None
    for rule in rules:
        required = set(rule.get("classes", []))
        if not required or not required.issubset(detected):
            continue
        if rule.get("type") == "caution":
            return rule
        if first_good is None:
            first_good = rule
    return first_good


def build_dosage_notices(counts, rules):
    """현재 감지된 클래스별 개수(counts)와 dosage.json 규칙을 비교해
    "한 번에 몇 알" 안내 문구 목록을 만든다.

    화면에 보이는 개수가 규칙의 권장 개수보다 많으면(같은 종류가 여러 알
    잡힌 경우) 실제 개수를 넣어 즉석에서 경고 문구를 만들고, 그렇지 않으면
    규칙에 미리 적어둔 message를 그대로 쓴다.
    """
    notices = []
    for c in sorted(counts):
        rule = rules.get(c)
        if not rule:
            continue
        recommended = rule.get("count", 1)
        detected = counts[c]
        if detected > recommended:
            message = f"{c} {detected}개 감지됨 — 한 번엔 {recommended}알만 드세요"
        else:
            message = rule.get("message", f"{c}는 한 번에 {recommended}알 드세요")
        notices.append({"class": c, "message": message})
    return notices


class FrameBroadcaster:
    """가장 최근 프레임 1장만 보관한다.

    클라이언트별 큐를 두지 않아, 느린 클라이언트가 있어도 지연이 계속
    쌓이지 않고 다음번엔 항상 최신 프레임으로 건너뛴다.
    """

    def __init__(self):
        self.latest = None  # type: Optional[bytes]
        self.combo = None  # type: Optional[dict]
        self.timings = []  # type: list
        self.dosage = []  # type: list
        self.frame_id = 0
        self._lock = threading.Lock()

    def publish(self, jpeg_bytes, combo, timings, dosage):
        with self._lock:
            self.latest = jpeg_bytes
            self.combo = combo
            self.timings = timings
            self.dosage = dosage
            self.frame_id += 1

    def snapshot(self):
        with self._lock:
            return self.latest, self.combo, self.timings, self.dosage, self.frame_id


def capture_loop(cap, model, broadcaster, args, combo_rules, timing_rules, dosage_rules, stop_event):
    """카메라 읽기 + 추론을 반복하는 블로킹 루프. 별도 스레드에서 돈다."""
    frame_count = 0
    window_start = time.monotonic()
    last_seen = {}  # 클래스 이름 -> (마지막으로 감지된 monotonic 시각, 그때의 개수)

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        if args.width and args.height:
            frame = cv2.resize(frame, (args.width, args.height))

        annotated, counts = infer_and_annotate(model, frame, conf=args.conf, iou=args.iou)

        now = time.monotonic()
        for c, n in counts.items():
            last_seen[c] = (now, n)
        # 최근 DETECTION_HOLD_SECS 이내에 본 클래스만 "현재 감지 중"으로 취급
        # (프레임마다 탐지가 깜빡이는 걸 완화). 오래된 항목은 같이 정리한다.
        last_seen = {c: v for c, v in last_seen.items() if now - v[0] <= DETECTION_HOLD_SECS}
        stable_counts = {c: v[1] for c, v in last_seen.items()}
        stable_classes = set(stable_counts.keys())

        active_combo = match_combo(stable_classes, combo_rules)
        active_timings = [
            {"class": c, "message": timing_rules[c]}
            for c in sorted(stable_classes)
            if c in timing_rules
        ]
        active_dosage = build_dosage_notices(stable_counts, dosage_rules)

        ok2, buf = cv2.imencode(
            ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality]
        )
        if ok2:
            broadcaster.publish(buf.tobytes(), active_combo, active_timings, active_dosage)

        # 체감이 아니라 수치로 FPS를 확인할 수 있게 주기적으로 로그를 남긴다
        # (Jetson Nano처럼 느린 보드에서 기대치와 비교하기 위함).
        frame_count += 1
        elapsed = time.monotonic() - window_start
        if elapsed >= 5.0:
            print(f"[stream] inference fps: {frame_count / elapsed:.1f}")
            frame_count = 0
            window_start = time.monotonic()


def create_app(args) -> FastAPI:
    app = FastAPI()
    broadcaster = FrameBroadcaster()
    stop_event = threading.Event()
    state = {}

    @app.on_event("startup")
    def _startup():
        print(f"[stream] 모델 로드: {args.model}")
        model = load_model(args.model, device=args.device)

        source = int(args.source) if args.source.isdigit() else args.source
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"카메라를 열 수 없습니다: {args.source}")

        combo_rules = load_combo_rules(args.combos)
        timing_rules = load_timing_rules(args.timings)
        dosage_rules = load_dosage_rules(args.dosage)

        thread = threading.Thread(
            target=capture_loop,
            args=(cap, model, broadcaster, args, combo_rules, timing_rules, dosage_rules, stop_event),
            daemon=True,
        )
        thread.start()

        state["cap"] = cap
        state["thread"] = thread
        print(f"[stream] 준비 완료. http://{args.host}:{args.port}/ 에서 확인하세요.")

    @app.on_event("shutdown")
    def _shutdown():
        stop_event.set()
        thread = state.get("thread")
        if thread is not None:
            thread.join(timeout=2.0)
        cap = state.get("cap")
        if cap is not None:
            cap.release()

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        last_id = -1
        last_sent = "__unset__"  # (combo, timings, dosage)와 절대 같을 수 없는 초기값
        interval = 1.0 / args.max_fps
        try:
            while True:
                await asyncio.sleep(interval)
                jpeg, combo, timings, dosage, frame_id = broadcaster.snapshot()
                if jpeg is None or frame_id == last_id:
                    continue
                # 배너/타이밍/복용량 상태가 바뀔 때만 텍스트 프레임을 추가로 보낸다
                # (느린 보드/네트워크에서 불필요한 전송을 줄이기 위함). 클라이언트는
                # 문자열 메시지는 UI 갱신으로, 바이너리 메시지는 이미지로 처리한다.
                current = (combo, timings, dosage)
                if current != last_sent:
                    await ws.send_text(
                        json.dumps(
                            {"combo": combo, "timings": timings, "dosage": dosage},
                            ensure_ascii=False,
                        )
                    )
                    last_sent = current
                await ws.send_bytes(jpeg)
                last_id = frame_id
        except WebSocketDisconnect:
            pass

    # index.html / app.js 서빙. "/ws"는 위에서 먼저 등록했으므로 겹치지 않는다.
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


def parse_args():
    parser = argparse.ArgumentParser(
        description="YOLOv8 알약 탐지 결과 실시간 웹소켓 스트리밍"
    )
    parser.add_argument(
        "--model", type=Path, default=DEFAULT_MODEL,
        help="가중치 경로 (기본: weights/best.pt)",
    )
    parser.add_argument(
        "--source", default="0", help="카메라 인덱스 또는 영상 경로 (기본: 0)"
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="바인드 주소 (기본: 0.0.0.0, LAN 전체 공개)"
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.75)
    parser.add_argument(
        "--device", default=None, help="예: 0 / cpu (기본: ultralytics 자동 선택)"
    )
    parser.add_argument(
        "--width", type=int, default=480,
        help="추론 전 리사이즈 폭 (Jetson Nano 성능 고려 기본값, 0이면 리사이즈 안 함)",
    )
    parser.add_argument(
        "--height", type=int, default=360,
        help="추론 전 리사이즈 높이 (0이면 리사이즈 안 함)",
    )
    parser.add_argument(
        "--max-fps", type=float, default=8.0, dest="max_fps",
        help="클라이언트로 보내는 최대 프레임 속도 (기본 8)",
    )
    parser.add_argument(
        "--jpeg-quality", type=int, default=80, dest="jpeg_quality",
        help="JPEG 인코딩 품질 0~100 (기본 80)",
    )
    parser.add_argument(
        "--combos", type=Path, default=DEFAULT_COMBOS,
        help="조합 배너 규칙 파일 경로 (기본: stream/combos.json, 없으면 기능 비활성화)",
    )
    parser.add_argument(
        "--timings", type=Path, default=DEFAULT_TIMINGS,
        help="복용 타이밍 안내 파일 경로 (기본: stream/timing.json, 없으면 기능 비활성화)",
    )
    parser.add_argument(
        "--dosage", type=Path, default=DEFAULT_DOSAGE,
        help="복용량 안내 파일 경로 (기본: stream/dosage.json, 없으면 기능 비활성화)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app(args)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

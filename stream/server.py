# -*- coding: utf-8 -*-
"""
server.py
USB 웹캠 영상에 YOLO 탐지 결과(bbox+라벨)를 입혀 WebSocket으로
실시간 스트리밍하는 서버. Jetson Nano 등 LAN 안의 보드에서 직접 돌리고,
같은 네트워크의 브라우저가 http://<host>:<port>/ 로 접속해서 본다.

사용법:
    python stream/server.py
    python stream/server.py --source 0 --width 480 --height 360 --max-fps 5
    python stream/server.py --model best.pt --device 0

동작 방식:
    카메라 읽기 + 추론은 블로킹 작업이라 별도 스레드(capture_loop)에서 돌리고,
    가장 최근 프레임 1장만 FrameBroadcaster에 보관한다. 클라이언트별로
    프레임을 큐에 쌓지 않으므로, 느린 클라이언트나 느린 보드에서도
    지연이 계속 누적되지 않고 항상 최신 프레임으로 건너뛴다.
"""

import argparse
import asyncio
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
DEFAULT_MODEL = REPO_ROOT / "best.pt"
STATIC_DIR = Path(__file__).resolve().parent / "static"


class FrameBroadcaster:
    """가장 최근 프레임 1장만 보관한다.

    클라이언트별 큐를 두지 않아, 느린 클라이언트가 있어도 지연이 계속
    쌓이지 않고 다음번엔 항상 최신 프레임으로 건너뛴다.
    """

    def __init__(self):
        self.latest = None  # type: Optional[bytes]
        self.frame_id = 0
        self._lock = threading.Lock()

    def publish(self, jpeg_bytes):
        with self._lock:
            self.latest = jpeg_bytes
            self.frame_id += 1

    def snapshot(self):
        with self._lock:
            return self.latest, self.frame_id


def capture_loop(cap, model, broadcaster, args, stop_event):
    """카메라 읽기 + 추론을 반복하는 블로킹 루프. 별도 스레드에서 돈다."""
    frame_count = 0
    window_start = time.monotonic()

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        if args.width and args.height:
            frame = cv2.resize(frame, (args.width, args.height))

        annotated = infer_and_annotate(model, frame, conf=args.conf, iou=args.iou)
        ok2, buf = cv2.imencode(
            ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality]
        )
        if ok2:
            broadcaster.publish(buf.tobytes())

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

        thread = threading.Thread(
            target=capture_loop,
            args=(cap, model, broadcaster, args, stop_event),
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
        interval = 1.0 / args.max_fps
        try:
            while True:
                await asyncio.sleep(interval)
                jpeg, frame_id = broadcaster.snapshot()
                if jpeg is None or frame_id == last_id:
                    continue
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
        help="가중치 경로 (기본: 저장소 루트의 best.pt)",
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
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app(args)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

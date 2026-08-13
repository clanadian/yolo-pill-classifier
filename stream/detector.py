# -*- coding: utf-8 -*-
"""YOLO 모델 로드, 추론, 시각화와 단계별 추론 시간 측정."""

from time import perf_counter

import cv2
import numpy as np

# JetPack 4.6의 TensorRT 8.0 Python 바인딩은 NumPy 1.24에서 제거된
# np.bool 별칭을 참조한다. 전역 패키지를 내리지 않고 엔진 로드 시에만
# 기존 바인딩이 기대하는 이름을 복원한다.
if "bool" not in np.__dict__:
    np.bool = np.bool_

from ultralytics import YOLO

# 데모용 표시 이름. best.pt는 원래 모양/색 기준 클래스(capsule, green_caplet, ...)로
# 학습되어 있지만, 데모 화면에서는 자주 먹는 영양제 이름으로 보여준다.
# 실제 학습 데이터(dataset/data.yaml, preprocess/*)는 그대로 두고, 추론 결과의
# 표시 이름만 바꾼다 — 재학습 불필요.
DEMO_SUPPLEMENT_NAMES = {
    0: "오메가3",   # capsule
    1: "마그네슘",  # green_caplet
    2: "유산균",    # mint_circle
    3: "칼슘",      # pink_caplet
    4: "비타민C",   # white_caplet
    5: "비타민D",   # yellow_caplet
}

# OpenCV putText는 한글 글리프를 지원하지 않으므로 빠른 렌더링 경로에서는
# 학습 클래스의 짧은 영문명을 사용한다. 검출 집계와 웹 UI 메시지는 위 한글
# 이름을 계속 사용한다.
FAST_DRAW_NAMES = {
    0: "Omega3",
    1: "Magnesium",
    2: "Probiotics",
    3: "Calcium",
    4: "VitaminC",
    5: "VitaminD",
}
BOX_COLORS = [
    (255, 120, 40),
    (60, 190, 90),
    (170, 220, 70),
    (220, 120, 190),
    (220, 220, 220),
    (40, 210, 240),
]


def load_model(weights_path, device=None):
    # trtexec로 만든 엔진에는 Ultralytics task 메타데이터가 없으므로 명시한다.
    # .pt에도 같은 값을 넘겨 두 백엔드의 로드 경로를 동일하게 유지한다.
    model = YOLO(str(weights_path), task="detect")
    if device is not None and not str(weights_path).endswith(".engine"):
        model.to(device)
    return model


def _draw_fast(frame, result):
    """PIL 기반 result.plot() 대신 OpenCV로 bbox와 ASCII 라벨을 그린다."""
    annotated = frame.copy()
    if result.boxes is None or len(result.boxes) == 0:
        return annotated

    for row in result.boxes.data.cpu().numpy():
        x1, y1, x2, y2, score, class_id = row[:6]
        class_id = int(class_id)
        color = BOX_COLORS[class_id % len(BOX_COLORS)]
        p1 = (int(x1), int(y1))
        p2 = (int(x2), int(y2))
        label = "{} {:.2f}".format(FAST_DRAW_NAMES.get(class_id, class_id), score)
        cv2.rectangle(annotated, p1, p2, color, 2, cv2.LINE_AA)
        (text_w, text_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
        )
        label_top = max(0, p1[1] - text_h - baseline - 4)
        cv2.rectangle(
            annotated,
            (p1[0], label_top),
            (p1[0] + text_w + 4, p1[1]),
            color,
            cv2.FILLED,
        )
        cv2.putText(
            annotated,
            label,
            (p1[0] + 2, max(text_h, p1[1] - baseline - 2)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
    return annotated


def infer_and_annotate(
    model, frame, conf=0.25, iou=0.75, draw=True, fast_draw=False
):
    """프레임을 추론해 시각화 결과, 클래스 개수, 단계별 시간을 반환한다."""
    model_start = perf_counter()
    results = model(frame, conf=conf, iou=iou, verbose=False)
    model_total_ms = (perf_counter() - model_start) * 1000.0
    result = results[0]

    # .pt뿐 아니라 TensorRT .engine도 같은 표시 이름을 사용한다. 엔진 백엔드는
    # model.model이 PyTorch 모듈이 아닐 수 있으므로 결과 객체에서만 이름을 바꾼다.
    result.names = DEMO_SUPPLEMENT_NAMES

    if draw:
        draw_start = perf_counter()
        annotated = _draw_fast(frame, result) if fast_draw else result.plot()
        draw_ms = (perf_counter() - draw_start) * 1000.0
    else:
        annotated = frame
        draw_ms = 0.0

    count_start = perf_counter()
    counts = {}
    if result.boxes is not None and len(result.boxes) > 0:
        names = result.names
        for c in result.boxes.cls.tolist():
            name = names[int(c)]
            counts[name] = counts.get(name, 0) + 1
    count_ms = (perf_counter() - count_start) * 1000.0

    # Ultralytics가 내부 동기화를 포함해 보고한 전처리/추론/후처리 시간이다.
    # model_total_ms는 Python 호출 전체 wall-clock이므로 세 값의 합과 다를 수 있다.
    speed = result.speed or {}
    timing = {
        "model_total_ms": model_total_ms,
        "preprocess_ms": float(speed.get("preprocess") or 0.0),
        "inference_ms": float(speed.get("inference") or 0.0),
        "postprocess_ms": float(speed.get("postprocess") or 0.0),
        "draw_ms": draw_ms,
        "count_ms": count_ms,
    }

    return annotated, counts, timing

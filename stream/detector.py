# -*- coding: utf-8 -*-
"""YOLO 모델 로드, 추론, 시각화와 단계별 추론 시간 측정."""

from time import perf_counter

from ultralytics import YOLO

# 데모용 표시 이름. best.pt는 원래 모양/색 기준 클래스(capsule, green_caplet, ...)로
# 학습되어 있지만, 데모 화면에서는 자주 먹는 영양제 이름으로 보여준다.
# 실제 학습 데이터(dataset/data.yaml, preprocess/*)는 그대로 두고, 이 표시
# 이름만 model.names를 덮어써서 바꾼다 — 재학습 불필요.
DEMO_SUPPLEMENT_NAMES = {
    0: "오메가3",   # capsule
    1: "마그네슘",  # green_caplet
    2: "유산균",    # mint_circle
    3: "칼슘",      # pink_caplet
    4: "비타민C",   # white_caplet
    5: "비타민D",   # yellow_caplet
}


def load_model(weights_path, device=None):
    model = YOLO(str(weights_path))
    if device is not None:
        model.to(device)
    # YOLO.names는 읽기 전용 프로퍼티(내부적으로 model.model.names를 가리킴)라
    # 직접 대입하면 AttributeError가 난다. 실제 dict는 내부 model.model에 있다.
    model.model.names = DEMO_SUPPLEMENT_NAMES
    return model


def infer_and_annotate(model, frame, conf=0.25, iou=0.75):
    """프레임을 추론해 시각화 결과, 클래스 개수, 단계별 시간을 반환한다."""
    model_start = perf_counter()
    results = model(frame, conf=conf, iou=iou, verbose=False)
    model_total_ms = (perf_counter() - model_start) * 1000.0
    result = results[0]

    draw_start = perf_counter()
    annotated = result.plot()
    draw_ms = (perf_counter() - draw_start) * 1000.0

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

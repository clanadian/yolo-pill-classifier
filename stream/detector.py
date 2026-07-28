# -*- coding: utf-8 -*-
"""
detector.py
yolov8_cam.py의 모델 로드 + 추론 + 시각화 패턴을 공용 함수로 뽑아둔 모듈.
stream/server.py가 이 함수들을 그대로 사용해, 탐지 로직이 여러 곳에서
따로 구현되지 않게 한다.
"""

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
    """프레임 한 장에 대해 추론하고, (bbox+라벨이 그려진 프레임, 클래스 이름 ->
    개수 딕셔너리)를 돌려준다. 개수는 "한 알만 드세요" 같은 복용량 안내
    (server.py의 build_dosage_notices)에, 클래스 존재 여부는 조합 배너 매칭
    (match_combo)에 쓰인다."""
    results = model(frame, conf=conf, iou=iou, verbose=False)
    result = results[0]
    annotated = result.plot()

    counts = {}
    if result.boxes is not None and len(result.boxes) > 0:
        names = result.names
        for c in result.boxes.cls.tolist():
            name = names[int(c)]
            counts[name] = counts.get(name, 0) + 1

    return annotated, counts

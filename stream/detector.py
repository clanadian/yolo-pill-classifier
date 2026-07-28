# -*- coding: utf-8 -*-
"""
detector.py
yolov8_cam.py의 모델 로드 + 추론 + 시각화 패턴을 공용 함수로 뽑아둔 모듈.
stream/server.py가 이 함수들을 그대로 사용해, 탐지 로직이 여러 곳에서
따로 구현되지 않게 한다.
"""

from ultralytics import YOLO


def load_model(weights_path, device=None):
    model = YOLO(str(weights_path))
    if device is not None:
        model.to(device)
    return model


def infer_and_annotate(model, frame, conf=0.25, iou=0.75):
    """프레임 한 장에 대해 추론하고, bbox+라벨이 그려진 프레임을 돌려준다."""
    results = model(frame, conf=conf, iou=iou, verbose=False)
    return results[0].plot()

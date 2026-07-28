yolo-pill-classifier 시스템 아키텍처
부가 안내 로직 (표시 전용, 실제 성분 판별 아님)

실시간 배포 — Jetson Nano

학습 (Person B)

데이터 파이프라인 (Person A)

실패

통과

ws://board:8000

사진 촬영
(폰 960x960 / 웹캠 640x480)

auto_label.py
Otsu 기반 자동 bbox

boundingRect 90%↑
extent ≥ 0.35 ?

labelImg
수동 라벨링

라벨 확정

color_fix_*.py
(LUT, 휘도+채도 보정)

split_and_build.py
train/val 분리 (85/15)

dataset/
images+labels+data.yaml

train_yolo.py
YOLOv8n, imgsz 640

runs/pill_yolo/weights/best.pt
(학습 체크포인트)

--export-best
(optimizer strip)

weights/best.pt
(배포용, 약 6MB)

USB 웹캠

capture_loop
(별도 스레드)

detector.py
infer_and_annotate()

FrameBroadcaster
최신 프레임 1장만 유지

server.py
FastAPI + WebSocket

브라우저
index.html + app.js

combos.json
조합 주의/권장

timing.json
복용 타이밍

dosage.json
1회 권장량
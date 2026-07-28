# stream/ — Jetson Nano 실시간 웹 스트리밍

USB 웹캠 영상에 YOLO 탐지 결과(bbox+라벨)를 입혀 WebSocket으로 실시간 스트리밍하는
서버. Jetson Nano 같은 보드가 카메라 캐처 + 추론 + 웹서버를 전부 직접 처리하고,
같은 LAN 안의 브라우저가 `http://<board-ip>:8000/` 로 바로 접속해서 본다.
포트포워딩·릴레이 서버·HTTPS는 다루지 않는다(LAN 전용).

## 실행

`best.pt`가 저장소 루트에 있어야 한다(`train/train_yolo.py --export-best`로 생성).

```bash
pip install -r requirements.txt   # fastapi, uvicorn[standard] 포함
python stream/server.py
```

브라우저로 `http://<보드 IP>:8000/` 접속.

### 자주 쓰는 옵션

```bash
# Jetson Nano처럼 느린 보드에서 보수적으로
python stream/server.py --width 480 --height 360 --max-fps 5

# 다른 카메라 인덱스 / 다른 가중치
python stream/server.py --source 1 --model runs/pill_yolo/weights/best.pt

# CPU로 강제 실행
python stream/server.py --device cpu
```

전체 옵션은 `python stream/server.py --help` 참고.

## Jetson Nano 참고 사항

원래 Jetson Nano(4GB)는 JetPack 4.6.x(Python 3.6, CUDA 10.2)에 묶여 있는 경우가
많아, 최신 `ultralytics` pip 패키지(Python >=3.8 요구)가 그대로 설치되지 않을 수
있다. JetPack 5/6은 오리지널 Nano에서 지원되지 않는다(Orin 전용).

- 이 프로젝트는 이미 Jetson Nano에서 `yolov8_cam.py`(`ultralytics`/`opencv-python`)가
  정상 동작하는 것을 확인한 환경을 전제로 한다. 그 환경에 `fastapi`,
  `uvicorn[standard]`만 추가로 설치하면 된다.
- 만약 처음부터 환경을 새로 구성해야 한다면, NVIDIA의 `l4t-ml` / `l4t-pytorch`
  Docker 컨테이너를 사용하는 것이 현실적인 방법이다(이 저장소는 해당 컨테이너
  구성을 자동화하지 않는다).
- Maxwell GPU(128 코어)에서 순수 `.pt` 추론은 640px 기준 체감 1~3 FPS로 느릴 수
  있다. `--width`/`--height`로 해상도를 낮추고 `--max-fps`로 전송 속도를 제한하는
  것은 이 때문이다. 콘솔에 5초 주기로 찍히는 `inference fps` 로그로 실제 속도를
  확인할 수 있다.
- 더 빠르게 하려면 `model.export(format="engine")`(TensorRT)로 변환 후
  `--model best.engine`으로 실행하는 것을 고려할 수 있다(이 저장소에서 자동화하지
  않음, 수동 후속 작업).

## 조합 배너 (`combos.json`)

인식된 클래스 조합에 대해 화면에 안내 배너를 띄우는 기능. `stream/combos.json`을
직접 편집해서 등록한 규칙만 매칭하며, 모델이 실제 성분 상호작용을 스스로
판단하는 게 아니다. 실제 학습 클래스는 색상/모양 기반(`capsule`, `pink_caplet`
등, `dataset/data.yaml` 참고)이라 실제 성분을 특정하지 못하지만, 데모 화면에서는
`stream/detector.py`의 `DEMO_SUPPLEMENT_NAMES`로 자주 먹는 영양제 이름
(오메가3/마그네슘/유산균/칼슘/비타민C/비타민D)으로 표시를 바꿔서 보여준다
(재학습 없이 표시 이름만 덮어쓰는 것 — 실제 성분 식별 기능 아님). 실제 복약
판단에는 쓰지 말 것.

```json
[
  {
    "classes": ["비타민D", "칼슘"],
    "type": "good",
    "message": "비타민D가 칼슘 흡수를 도와줘요 — 아침 식후에 함께 드세요"
  },
  {
    "classes": ["칼슘", "마그네슘"],
    "type": "caution",
    "message": "두 미네랄이 흡수 경로를 나눠 써요 — 2~3시간 간격을 두는 게 좋아요"
  }
]
```

- `classes`: 이 목록의 클래스가 **모두** 현재 프레임에서 감지되면 규칙이 발동
  (더 감지되는 다른 클래스가 있어도 무방).
- `type`: `"good"` 또는 `"caution"`. 여러 규칙이 동시에 맞으면 `caution`을
  우선 노출한다(경고를 좋은 조합 배너에 가려서 안 보이게 하지 않기 위함).
- 파일이 없으면 서버는 경고 로그만 남기고 배너 기능 없이 정상 동작한다.
- 다른 경로를 쓰려면 `--combos <경로>` 옵션 사용.
- 저장소에 커밋된 `stream/combos.json`은 예시일 뿐이니 실제 사용 전에
  내용을 직접 검토/수정할 것.

## 카메라 장치 확인 (Jetson)

```bash
ls /dev/video0
groups   # 실행 계정이 video 그룹에 속해 있는지 확인
```

## 범위 밖

HTTPS/인증, LAN 밖 노출(포트포워딩/DDNS/클라우드 릴레이), 다중 카메라, 녹화/저장,
모바일 앱, WebRTC/MJPEG 등 다른 전송 방식은 다루지 않는다.

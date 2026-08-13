# stream/ — Jetson Nano 실시간 웹 스트리밍

USB 웹캠 영상에 YOLO 탐지 결과(bbox+라벨)를 입혀 WebSocket으로 실시간 스트리밍하는
서버. Jetson Nano 같은 보드가 카메라 캐처 + 추론 + 웹서버를 전부 직접 처리하고,
같은 LAN 안의 브라우저가 `http://<board-ip>:8000/` 로 바로 접속해서 본다.
포트포워딩·릴레이 서버·HTTPS는 다루지 않는다(LAN 전용).

## 실행

`model/best.pt`가 있어야 한다(`training/train_yolo.py --export-best`로 생성).

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

### 단계별 latency 기록

```bash
python3 -u stream/server.py \
  --width 480 --height 360 --max-fps 5 \
  --metrics-csv results/baseline_run1.csv \
  --warmup-secs 30
```

종료하면 프레임별 capture, resize, preprocess, inference, postprocess, draw,
JPEG encode, 전체 처리시간이 CSV에 저장되고, warm-up 이후의 평균/P50/P95가
콘솔에 출력된다. `--metrics-csv`를 주지 않으면 계측값을 수집하지 않는다.

동일한 저장 영상을 반복 재생하거나 bbox 렌더링 비용을 분리할 때는 다음 옵션을 쓴다.

```bash
python3 -u stream/server.py --source benchmark.avi --loop-source \
  --metrics-csv results/baseline_video.csv

python3 -u stream/server.py --source benchmark.avi --loop-source --no-draw \
  --metrics-csv results/no_draw_video.csv

python3 -u stream/server.py --source benchmark.avi --loop-source --fast-draw \
  --metrics-csv results/fast_draw_video.csv
```

`--fast-draw`는 느린 PIL 기반 한글 bbox 라벨 대신 OpenCV 기반 영문 라벨을
사용한다. 조합/복용량 등 웹 UI의 한글 안내와 검출 집계 이름은 유지된다.

### TensorRT 엔진 빌드(Jetson에서만)

```bash
python3 stream/build_tensorrt.py --weights model/best.pt --precision fp16

python3 stream/server.py --model model/best_fp16.engine --fast-draw \
  --width 480 --height 360 --max-fps 5
```

스크립트는 ONNX opset 12를 내보내고 `trtexec`로 엔진을 만든 뒤 Ultralytics가
요구하는 task/names/imgsz 메타데이터를 붙인다. JetPack 4.6의 TensorRT 8.0과
NumPy 1.24 사이 `np.bool` 호환은 모델 로더가 처리한다. 엔진은 GPU와 TensorRT
버전에 종속되고 빌드에 수 분이 걸리므로 `.onnx`/`.engine`은 Git에서 제외한다.

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
- 고정 영상·480×360·warm-up 30초·180초·3회 조건에서 PyTorch 기본 경로는
  6.34 FPS, TensorRT FP16 + `--fast-draw`는 13.77 FPS였다. inference는
  63.14→46.26ms, draw는 69.44→1.12ms로 줄었다. GPU 최고 온도는 32°C였다.
  과거 특정 SD카드 상태에서 관찰한 3.3~4.3 FPS 저하는 카드 스왑 후 재현되지
  않았으므로 일반 성능값으로 사용하지 않는다. 전체 방법과 정확도 비교는
  [`../docs/jetson_yolov8_optimization_roadmap.md`](../docs/jetson_yolov8_optimization_roadmap.md)
  참고.

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
    "message": "두 미네랄이 흡수 경로를 나눠 써요 — 2-3시간 간격을 두는 게 좋아요"
  }
]
```

- `classes`: 이 목록의 클래스가 **모두** 현재 프레임에서 감지되면 규칙이 발동
  (더 감지되는 다른 클래스가 있어도 무방).
- `type`: `"good"` 또는 `"caution"`. 여러 규칙이 동시에 맞으면 `caution`을
  우선 노출한다(경고를 좋은 조합 배너에 가려서 안 보이게 하지 않기 위함).
- `message`: **관련된 클래스 이름을 반드시 문구에 직접 써야 한다.** "두 미네랄이",
  "둘 다" 같은 대명사만 쓰면 사용자가 배너만 보고 뭘 말하는지 알 수 없다.
  (예: "두 미네랄이 흡수 경로를 나눠 써요" ❌ → "칼슘과 마그네슘은 흡수 경로를
  나눠 써요" ✅)
- 파일이 없으면 서버는 경고 로그만 남기고 배너 기능 없이 정상 동작한다.
- 다른 경로를 쓰려면 `--combos <경로>` 옵션 사용.
- 저장소에 커밋된 `stream/combos.json`은 예시일 뿐이니 실제 사용 전에
  내용을 직접 검토/수정할 것.
- 화면에서는 조합 배너가 영상 위에 겹쳐 뜨지 않고, 영상 아래 별도 영역에 표시된다.

## 복용 타이밍 안내 (`timing.json`)

조합과 별개로, 현재 화면에 감지된 클래스 각각에 대해 "언제 먹으면 좋은지"를
조합 배너 아래에 목록으로 보여주는 기능. `stream/timing.json`은 클래스 이름 →
안내 문구로 이루어진 단순한 딕셔너리다.

```json
{
  "오메가3": "식사와 함께 드시면 흡수가 잘돼요",
  "비타민D": "기름기 있는 식사와 함께(아침 또는 점심) 드세요"
}
```

- 현재 감지 중인 클래스 중 이 파일에 항목이 있는 것만 표시된다(없는 클래스는
  조용히 건너뜀).
- 조합 배너와 마찬가지로 감지가 잠깐 끊겨도(최대 1.5초) 목록이 바로 사라지지
  않는다.
- 파일이 없으면 서버는 경고 로그만 남기고 이 목록 없이 정상 동작한다.
- 다른 경로를 쓰려면 `--timings <경로>` 옵션 사용.

## 복용량 안내 (`dosage.json`)

타이밍 안내 아래에, 클래스별 "한 번에 몇 알" 권장량을 보여주는 기능.
`stream/dosage.json`은 클래스 이름 → `{"count": 권장개수, "message": 안내문구}`
딕셔너리다.

```json
{
  "오메가3": {"count": 1, "message": "오메가3는 한 번에 1알만 드세요"},
  "칼슘": {"count": 2, "message": "칼슘은 한 번에 2알 드세요"}
}
```

- 화면에 보이는 같은 클래스의 개수가 `count`보다 많으면(예: 오메가3 2알이
  동시에 잡힘), `message`를 쓰지 않고 실제 개수를 넣어 즉석에서
  "오메가3 2개 감지됨 — 한 번엔 1알만 드세요" 같은 문구를 만든다(조사 없이
  써서 어떤 클래스 이름이 와도 문법이 안 깨지게 함). `count` 이하로 잡히면
  `message`를 그대로 보여준다.
- 타이밍/조합 배너와 마찬가지로 감지가 잠깐 끊겨도(최대 1.5초) 목록이 바로
  사라지지 않는다.
- 파일이 없으면 서버는 경고 로그만 남기고 이 목록 없이 정상 동작한다.
- 다른 경로를 쓰려면 `--dosage <경로>` 옵션 사용.

## 카메라 장치 확인 (Jetson)

```bash
ls /dev/video0
groups   # 실행 계정이 video 그룹에 속해 있는지 확인
```

## 범위 밖

HTTPS/인증, LAN 밖 노출(포트포워딩/DDNS/클라우드 릴레이), 다중 카메라, 녹화/저장,
모바일 앱, WebRTC/MJPEG 등 다른 전송 방식은 다루지 않는다.

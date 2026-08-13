# Jetson Nano YOLOv8 최적화 로드맵

> 목표: 기존 Jetson Nano 알약 탐지 프로젝트에서 **실제 병목을 확인하고,
> TensorRT FP16 적용 전후를 수치로 비교한다.**

> 상태: **2026-08-13 완료.** 고정 영상 3회 반복 측정과 정확도 검증까지 마쳤으며,
> 결과는 5절에 정리했다.

이번 작업은 프로젝트를 새로 만드는 것이 아니다. 현재 코드에 최소한의 계측과
최적화를 추가해 다음 질문에 답하는 것이 목적이다.

1. 프레임 처리 중 어느 단계가 가장 느린가?
2. TensorRT FP16으로 추론 시간이 얼마나 줄었는가?
3. 추론 개선이 전체 FPS 개선으로 이어졌는가?
4. 남은 병목은 무엇인가?

---

## 1. 현재 상태

- Jetson Nano, JetPack 4.6, L4T 32.6.1
- YOLOv8n 기반 6종 알약 탐지
- USB 카메라와 FastAPI/WebSocket 웹 UI
- mAP50 0.974, mAP50-95 0.803
- 과거 특정 SD카드 상태에서만 3.3~4.3 FPS 저하가 관찰됐으나 카드 스왑 후
  재현되지 않음(보드 고유 결함 가설 배제, 세부 원인은 카드 초기화로 미확정)
- CPU 한 코어 지속 점유, GPU 사용률 간헐적 상승
- RAM 약 3.1~3.2 GB
- 고정 영상 기준선에서 `inference_ms` 63.14ms, `draw_ms` 69.44ms로 확인

현재 `stream/server.py`의 주요 처리 구간은 다음과 같다.

```text
cap.read()
  → resize
  → YOLO preprocess / inference / postprocess
  → bbox draw
  → JPEG encode
  → 최신 프레임 publish
```

WebSocket 전송은 이미 별도의 비동기 루프에서 수행되므로, 우선 위 구간만 측정한다.

---

## 2. 이번에 할 일

### 필수 1 — 단계별 latency 측정

다음 값만 프레임별로 기록한다.

| 지표 | 의미 |
|---|---|
| `capture_ms` | 카메라 프레임 읽기 |
| `resize_ms` | 입력 크기 변경 |
| `preprocess_ms` | YOLO 입력 전처리 |
| `inference_ms` | 모델 추론 |
| `postprocess_ms` | NMS 등 후처리 |
| `draw_ms` | bbox와 라벨 그리기 |
| `encode_ms` | JPEG 인코딩 |
| `total_ms` | 한 프레임 전체 처리 |

`preprocess_ms`, `inference_ms`, `postprocess_ms`는 Ultralytics의
`result.speed`를 사용한다. 나머지는 `time.perf_counter()`로 측정한다.

```python
result = model(frame, conf=conf, iou=iou, verbose=False)[0]

preprocess_ms = result.speed.get("preprocess")
inference_ms = result.speed.get("inference")
postprocess_ms = result.speed.get("postprocess")
```

결과는 CSV 한 파일로 저장한다.

```csv
timestamp,frame_id,capture_ms,resize_ms,preprocess_ms,inference_ms,postprocess_ms,draw_ms,encode_ms,total_ms
```

실행 종료 시 각 항목의 평균, P50, P95를 출력한다. 처음 30초는 warm-up으로 제외한다.

### 필수 2 — Baseline 측정

기존 PyTorch/Ultralytics 경로를 다음 조건으로 측정한다.

- 입력 480×360
- warm-up 30초
- 측정 3~5분
- 동일한 카메라 위치와 알약 배치
- 가능하면 같은 영상 파일로 추가 측정
- 3회 반복

같이 기록할 항목:

- 처리 FPS
- 단계별 평균/P50/P95 latency
- CPU/GPU 사용률
- RAM과 온도
- JetPack, CUDA, TensorRT, Ultralytics 버전

시스템 상태는 기존처럼 `tegrastats` 로그를 사용한다. 별도의 대규모 benchmark
프레임워크는 만들지 않는다.

### 필수 3 — Draw 비용 격리

동일 영상에서 `result.plot()` 포함/생략을 한 번씩 비교한다. 생략 경로는 최종 기능이
아니라 렌더링 비용의 상한을 확인하는 ablation으로만 사용한다.

### 필수 4 — TensorRT FP16 비교

기존 `model/best.pt`를 Jetson Nano에서 FP16 TensorRT engine으로 변환한다.
TensorRT engine은 GPU와 TensorRT 버전에 종속되므로 다른 PC에서 만들어 복사하지 않는다.

비교 대상은 두 개뿐이다.

| 버전 | Backend | Pipeline |
|---|---|---|
| Baseline | PyTorch/Ultralytics | 기존 구조 |
| Optimized | TensorRT FP16 | 기존 구조 |

두 버전을 같은 조건에서 각각 3회 측정한다.

비교 항목:

- inference 평균/P50/P95
- total 평균/P50/P95
- 처리 FPS
- CPU/GPU 사용률
- RAM과 온도

FP16 정확도는 기존 validation 161장으로 확인한다.

- 동일한 `imgsz`, confidence, IoU
- mAP50
- mAP50-95
- 클래스별 성능에 큰 하락이 없는지 확인

TensorRT 적용 후 추론만 빨라지고 전체 FPS 증가가 작다면 실패가 아니다. 예를 들어
JPEG encode나 draw가 다음 병목이 됐다는 결과를 그대로 기록한다.

---

## 3. 측정 후 필요할 때만 할 일

### Draw 최적화

TensorRT 적용 뒤 기본 draw가 가장 큰 병목으로 남아 선택형 `--fast-draw`를 구현했다.
OpenCV로 bbox·신뢰도·영문 클래스명을 그리고, 웹 UI의 한글 안내와 검출 집계 이름은
유지한다. 기존 한글 bbox 경로도 기본값으로 보존한다.

### 캡처/처리 분리

단계별 측정에서 `cap.read()` 대기나 직렬 구조가 실제 병목으로 확인될 때만 적용한다.

```text
Capture thread
  → 최신 프레임 1장
  → Inference/draw/encode thread
  → FrameBroadcaster
```

프레임 큐를 길게 쌓지 않고 최신 프레임 하나만 유지한다. 최소한 다음 값만 추가로
기록한다.

- 캡처한 프레임 수
- 처리한 프레임 수
- 새 프레임으로 교체되어 처리하지 않은 프레임 수

구조를 변경했다면 다음 세 버전을 비교한다.

| 버전 | Backend | Pipeline |
|---|---|---|
| A | PyTorch | 기존 구조 |
| B | TensorRT FP16 | 기존 구조 |
| C | TensorRT FP16 | 캡처/처리 분리 |

이 단계는 TensorRT 비교가 끝난 뒤 결정한다. 이번 고정 입력 측정에서 `capture_ms`가
평균 2.86ms로 전체의 2% 미만이어서 처리량 병목이 아니므로 생략했다.

---

## 4. 이번에는 하지 않을 것

- TensorRT INT8
- 전체 코드 C++ 재작성
- DeepStream 파이프라인 구현
- Docker와 systemd 구성
- 브라우저까지의 정밀 End-to-End latency 측정
- 30분 이상 장시간 실험 자동화
- UART, I2C, CAN, MCU, ROS2 기능 추가
- GMSL2, PCIe, UEFI 관련 기능 추가

DeepStream은 공고와 관련성이 있지만 이번 핵심 결과가 완성된 후 시간이 남을 때만
별도 확장한다. 로드맵의 완료 조건에는 포함하지 않는다.

---

## 5. 결과 표

측정 조건: `.107` Jetson Nano + 검증된 `.108` SD카드, JetPack 4.6/L4T 32.6.1,
TensorRT 8.0.1.6, 640×480 MJPEG 고정 영상, 서버 입력 480×360, warm-up 30초,
180초 실행, 브라우저 WebSocket 연결, 각 최종 경로 3회 반복.

| Backend / draw | FPS | Inference 평균 | Draw 평균 | Total 평균 | Total P95 |
|---|---:|---:|---:|---:|---:|
| PyTorch / 기본 한글 | 6.34 | 63.14ms | 69.44ms | 157.71ms | 163.83ms |
| PyTorch / draw 생략(1회) | 11.51 | 62.55ms | 0ms | 86.89ms | 89.34ms |
| TensorRT FP16 / 기본 한글 | 7.41 | 46.28ms | 62.90ms | 135.01ms | 159.12ms |
| TensorRT FP16 / OpenCV fast | **13.77** | **46.26ms** | **1.12ms** | **72.65ms** | **74.02ms** |

3회 total 평균은 PyTorch 157.94/157.49/157.71ms, TensorRT 기본 draw
134.95/134.93/135.15ms, 최종 fast draw 72.71/72.66/72.56ms였다.

정확도:

| Backend (`imgsz=640`, `batch=1`, `rect=False`) | mAP50 | mAP50-95 |
|---|---:|---:|
| PyTorch FP32 | 0.96046 | 0.68069 |
| TensorRT FP16 | 0.96073 | 0.68150 |

고정 shape 엔진과 비교하려고 두 backend 모두 square 입력으로 맞췄다. PyTorch의
`rect=True` 결과(0.97603/0.81132)를 엔진 결과와 직접 비교하면 입력 전처리 정책이
달라지므로 변환 정확도 비교로 사용하지 않는다.

측정 결과 설명에는 다음 세 가지만 포함한다.

1. 실제로 가장 오래 걸린 단계
2. TensorRT FP16 적용 후 inference 및 전체 처리시간 변화
3. 남은 병목과 다음 개선 방향

---

## 6. 구현 순서

```text
1. detector.py가 Ultralytics 세부 timing을 반환하도록 수정
2. server.py에서 capture/resize/draw/encode/total 시간 측정
3. CSV 저장과 평균/P50/P95 요약 추가
4. 동일 저장 영상으로 PyTorch baseline 3회 측정
5. draw 포함/제외 ablation
6. Jetson에서 TensorRT FP16 engine 생성
7. FP16 정확도 확인
8. TensorRT 경로 3회 측정
9. OpenCV fast draw 구현 및 3회 재측정
10. 비교표와 병목 전환 해석 작성
11. 캡처 병목이 아니므로 캡처/처리 추가 분리는 생략
```

권장 커밋:

```text
feat: add per-stage latency measurement
bench: record PyTorch baseline results
feat: add TensorRT FP16 inference
bench: compare PyTorch and TensorRT performance
docs: document bottleneck and optimization results
```

---

## 7. 완료 기준

- [x] 단계별 latency가 CSV로 저장된다.
- [x] 평균/P50/P95가 계산된다.
- [x] PyTorch baseline을 동일 조건에서 3회 측정했다.
- [x] 동일 영상에서 draw 포함/제외 비용을 확인했다.
- [x] Jetson Nano에서 TensorRT FP16 engine을 생성하고 실행했다.
- [x] FP16 정확도를 기존 validation 데이터로 확인했다.
- [x] TensorRT 경로를 동일 조건에서 3회 측정했다.
- [x] inference와 전체 FPS의 개선 폭을 각각 설명했다.
- [x] 남은 draw 병목을 확인하고 선택형 경량 경로를 구현했다.
- [x] 캡처/처리 추가 분리를 생략한 근거를 확인했다.
- [x] README와 보고서에 비교표와 결론을 정리했다.

최종적으로 다음 문장을 실제 숫자로 설명할 수 있으면 완료다.

> Jetson Nano YOLOv8 실시간 탐지 파이프라인의 단계별 latency를 측정해 병목을 확인하고,
> TensorRT FP16 적용 전후의 추론 지연·전체 FPS·정확도를 동일 조건에서 비교했다.

이 정도면 기존의 “Jetson에서 YOLO를 실행하고 자원 사용량을 확인했다”에서
“병목을 찾아 실제 최적화를 적용하고 효과를 검증했다”로 프로젝트 수준을 충분히
높일 수 있다.

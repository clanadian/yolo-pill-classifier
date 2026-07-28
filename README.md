# yolo-pill-classifier

YOLOv8을 학습해 6종 알약을 실시간으로 탐지하고, Jetson Nano에서 웹 인터페이스를
통해 복용 정보와 조합 주의사항까지 제공하는 프로젝트입니다.

## 주요 기능

- ✅ 사진 촬영 → 자동 Bounding Box(bbox) 라벨링 → 수동 검수
- ✅ YOLOv8 학습 (로컬 GPU / Colab)
- ✅ Jetson Nano 실시간 추론
- ✅ 6종 알약 동시 탐지
- ✅ 복용 조합 주의 배너 · 복용량 · 복용 타이밍 안내
- ✅ FastAPI·WebSocket 기반 실시간 웹 스트리밍

<video src="https://github.com/user-attachments/assets/9fc1c7e3-b32c-4d7b-946e-8a9aced14672" width="600" controls></video>

**실시간 탐지 데모** — 웹캠으로 여러 알약을 동시에 인식해 종류·이름을 표시합니다.
실시간 웹캠뿐 아니라 저장된 영상 파일도 분석할 수 있습니다 (실행 방법은 아래
[실시간 데모](#실시간-데모-jetson-nano) 참고). 웹캠과 저장된 영상 모두 동일한
추론 파이프라인을 사용합니다.

![전체 기능 스크린샷](demo/all.png)

6종 동시 탐지, 조합 주의 배너, 복용 타이밍/복용량 안내까지 한 화면에서 확인할 수
있습니다. 다른 조합 예시는 [`demo/`](demo/) 폴더 참고.

## 결과

| 항목 | 값 |
|---|---|
| 모델 | YOLOv8n |
| 입력 해상도 | 640×640 |
| 클래스 수 | 6종 |
| 검증 mAP50 | **0.974** |
| 검증 mAP50-95 | **0.803** |
| 추론 플랫폼 | Jetson Nano (JetPack 4.6, t210ref) |
| 실측 FPS | 초기 5~7fps → 1분 전후 3.3~4.3fps로 수렴 (대표값 약 3.5~4fps) |
| 웹 UI | FastAPI + WebSocket |

클래스별 상세 지표(precision/recall/mAP), FPS 측정 방법론 3회 재현 결과는
[docs/report.md](docs/report.md) 5~6번 항목 참고.

## 아키텍처

```text
사진 촬영
    │
    ▼
자동 Bounding Box 라벨링 (auto_label.py)
    │
    ▼
수동 검수 → train/val 분리 (split_and_build.py)
    │
    ▼
색감 보정 (LUT, preprocess/color_fix/)
    │
    ▼
YOLOv8 학습 (train_yolo.py)
    │
    ▼
weights/best.pt
    │
    ▼
Jetson Nano 추론 (stream/server.py)
    │
    ▼
FastAPI + WebSocket
    │
    ▼
웹 브라우저
```

## 클래스 (6종, id 0~5)

<table>
<tr>
<th width="16.6%">0 capsule</th>
<th width="16.6%">1 green_caplet</th>
<th width="16.6%">2 mint_circle</th>
<th width="16.6%">3 pink_caplet</th>
<th width="16.6%">4 white_caplet</th>
<th width="16.6%">5 yellow_caplet</th>
</tr>
<tr>
<td><img src="docs/images/capsule_thumb.jpg" width="100%"></td>
<td><img src="docs/images/green_caplet_thumb.jpg" width="100%"></td>
<td><img src="docs/images/mint_circle_thumb.jpg" width="100%"></td>
<td><img src="docs/images/pink_caplet_thumb.jpg" width="100%"></td>
<td><img src="docs/images/white_caplet_thumb.jpg" width="100%"></td>
<td><img src="docs/images/yellow_caplet_thumb.jpg" width="100%"></td>
</tr>
</table>

## 폴더 구조

```
.
├── dataset/              # 학습용 최종 데이터셋 (images/labels train,val + data.yaml)
├── preprocess/           # 라벨링 파이프라인: auto_label.py, split_and_build.py
├── train/                # 학습 스크립트: train_yolo.py
├── notebooks/
│   └── train_on_colab.ipynb  # Colab(T4 GPU)에서 학습하고 싶을 때
├── weights/
│   └── best.pt           # 학습된 가중치 (--export-best로 생성, 데모가 읽는 기본 경로)
├── stream/               # Jetson Nano 실시간 웹 스트리밍 데모
├── docs/
│   ├── report.md         # 트러블슈팅 로그 (문제/원인/조치 기록)
│   ├── update.md         # 날짜별 진행 상황 및 팀원 간 인수인계 메모
│   └── pill_combo_plan.md # 알약 조합 안내 배너 기능 기획서
└── requirements.txt
```

## 설치 (로컬 PC — 전처리/학습용)

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

Jetson Nano(ARM64, JetPack 4.6 · Python 3.6 베이스)는 이 conda 환경을 그대로 쓸 수
없습니다. Jetson 쪽 세팅은 [실시간 데모](#실시간-데모-jetson-nano) 섹션과
[stream/README.md](stream/README.md)를 따로 참고하세요.

## 데이터셋 파이프라인 (전처리/라벨링)

새로 찍은 사진을 클래스별 폴더(`capsule/`, `green_caplet/`, `mint_circle/`,
`pink_caplet/`, `white_caplet/`, `yellow_caplet/`)에 넣은 뒤:

```bash
# 1. 자동 bbox 라벨링 (+ 미리보기로 검수)
python preprocess/auto_label.py --input_dir <원본사진폴더> --review
#   _review/ 폴더에서 박스 확인 → 이상한 것만 labelImg 등으로 수동 보정

# 2. train/val 분리 + data.yaml 생성
python preprocess/split_and_build.py --input_dir <원본사진폴더> --output_dir dataset --val_ratio 0.15
```

결과물: `dataset/images/{train,val}/`, `dataset/labels/{train,val}/`, `dataset/data.yaml`.
저대비(흰 배경+흰 알약 등) 케이스나 자동 라벨링 실패/오탐 사례는 `docs/report.md`에
원인과 대응 방법이 정리되어 있습니다.

---

> **아래 데모/학습 파트는 2026-07-28 기준 실제로 동작·수치를 검증했습니다**
> (모델 지표 재현, Jetson Nano 실측 FPS, 데이터셋 무결성 — `docs/report.md` 5~7번
> 항목). 다만 팀원이 계속 다듬고 있는 영역이라 세부 옵션은 이 문서보다 앞서
> 바뀔 수 있습니다.

## 실시간 데모 (Jetson Nano)

학습된 가중치 `weights/best.pt`가 저장소에 일반 파일로 포함되어 있어(Git LFS
아님, clone하면 바로 받아짐) 따로 학습하지 않아도 바로 실행할 수 있습니다.

> Jetson Nano는 JetPack 버전 제약 때문에 `ultralytics`/`opencv-python`을
> `requirements.txt`로 그냥 설치하기 어려운 경우가 많습니다. YOLOv8 추론이 이미
> 되는 환경이라는 전제로, 여기서 새로 필요한 건 `fastapi`·`uvicorn[standard]`뿐입니다
> (둘 다 `requirements.txt`에 포함되어 있음). 처음부터 새로 세팅해야 한다면
> `stream/README.md`의 Jetson Nano 참고 사항을 먼저 보세요.

```bash
python stream/server.py
```

Jetson Nano처럼 느린 보드에서는 해상도/전송 프레임을 낮춰서 시작하는 걸 권장합니다:

```bash
python3 stream/server.py --width 480 --height 360 --max-fps 5
```

브라우저로 `http://<보드 IP>:8000/` 접속하면 웹캠 영상에 탐지 결과가 얹혀 보입니다.
Jetson Nano 세팅, 옵션, 성능 관련 참고사항은 `stream/README.md`를 참고하세요.

## 학습

로컬 GPU:

```bash
python train/train_yolo.py --device 0 --export-best
```

`--data`를 안 주면 `dataset/` → `dataset_yolo/` → `dataset_yolo_colab/` 순으로 자동
탐지하고, 학습 전에 라벨/클래스 정합성을 먼저 검사합니다. 자세한 옵션은
`python train/train_yolo.py --help` 참고.

Colab(T4 GPU)에서 돌리려면 `notebooks/train_on_colab.ipynb`를 열어서 순서대로
실행하면 됩니다(저장소를 clone하면 코드와 `dataset/`이 같이 받아짐).

학습이 끝나면 `runs/`에 결과가 저장되고, `--export-best`를 주면 `weights/best.pt`로
복사됩니다.

## 문서

- [docs/report.md](docs/report.md) — 라벨링/전처리/학습 준비 과정에서 있었던 문제와 해결 과정 기록
- [docs/update.md](docs/update.md) — 날짜별 진행 상황, 다음 할 일, 팀원 간 인수인계 메모
- [docs/pill_combo_plan.md](docs/pill_combo_plan.md) — 알약 조합 안내 배너 기능(좋은
  조합/확인 필요 조합) 기획서. `stream/combos.json`·`timing.json`·`dosage.json`으로
  구현 완료

## 주요 트러블슈팅

- 흰 배경·흰 알약 조합에서 자동 라벨링이 "성공"으로 뜨면서도 조용히 실패하는 문제를
  발견 → 검증 필터 추가, 잔여 케이스는 수동 검수로 보완
- 조명 조건에 따라 흰색·핑크 알약이 서로 오분류되는 문제를 클래스별 색감 보정(LUT)으로 개선
- Jetson Nano 장시간 구동 시 FPS가 3.3~4.3으로 수렴하는 현상을 3회 재현 측정,
  열 스로틀링이 아님을 확인

자세한 원인 분석과 해결 과정은 [docs/report.md](docs/report.md)에 정리했습니다.

## 성과

- 데이터 촬영·라벨링부터 학습, Jetson Nano 배포, 웹 UI까지 전체 파이프라인을 직접 구축
- 검증 mAP50 0.974 · mAP50-95 0.803 달성 (자세한 수치는 위 [결과](#결과) 참고)
- 반복적으로 발견된 자동 라벨링/색감 오류 사례를 원인 분석 후 재현 가능한 방식으로 해결

## 한계 및 개선 방향

- 현재 6종 알약만 지원 — 반투명 캡슐(`purple_pill`)은 배경에 따라 색이 크게 달라지는
  데이터 일관성 문제로 제외됨 ([docs/report.md](docs/report.md) 2번 항목)
- 단일 카메라·한정된 촬영 환경(조명/배경)에서 수집한 데이터라 일반화에 한계 있음 —
  `white_caplet`은 색감 보정 후에도 mAP50-95 0.645로 전 클래스 중 최저, 잔여 약점으로 남음
- Jetson Nano에서는 실시간성이 제한적(약 3.5~4fps) — TensorRT 변환이나 더 가벼운
  모델로 개선 여지 있음 ([stream/README.md](stream/README.md) 참고, 자동화는 안 돼있음)

## 역할 분담

### 데이터 파이프라인
- 알약 촬영 및 자동 Bounding Box 라벨링(`preprocess/auto_label.py`)
- 저대비/오탐 라벨 수동 검수·보정
- 클래스별 색감 보정 LUT(`preprocess/color_fix/`)
- 데이터셋 구성 및 train/val 분리(`dataset/`, `data.yaml`)

### 모델 학습·배포
- YOLOv8 학습 파이프라인(`train/train_yolo.py`)
- Jetson Nano 배포
- FastAPI 웹 데모(`stream/`)
- 복용 정보(타이밍·복용량·조합 주의) UI 구현

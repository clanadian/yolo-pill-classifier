# yolo-pill-classifier

YOLOv8을 학습해 6종 알약을 실시간으로 탐지하고, Jetson Nano에서 웹 인터페이스를 통해 복용 정보와 조합 주의사항까지 제공하는 프로젝트다.

## 주요 기능

- ✅ 사진 촬영 → 자동 Bounding Box(bbox) 라벨링 → 수동 검수
- ✅ YOLOv8 학습 (로컬 GPU / Colab)
- ✅ Jetson Nano 실시간 추론
- ✅ 6종 알약 동시 탐지
- ✅ 복용 조합 주의 배너 · 복용량 · 복용 타이밍 안내
- ✅ FastAPI·WebSocket 기반 실시간 웹 스트리밍

## 데모 영상

<video src="https://github.com/user-attachments/assets/1699e528-d910-43a6-86cc-232d9a9aed14" width="600" controls></video>

**실시간 탐지 데모** — 웹캠으로 여러 알약을 동시에 인식해 종류·이름을 표시한다. 실시간 웹캠뿐 아니라 저장된 영상 파일도 분석할 수 있다 (실행 방법은 아래 [실시간 데모](#실시간-데모-jetson-nano) 참고). 웹캠과 저장된 영상 모두 동일한 추론 파이프라인을 사용한다.

![전체 기능 스크린샷](demo/all.png)

6종 동시 탐지, 조합 주의 배너, 복용 타이밍/복용량 안내까지 한 화면에서 확인할 수 있다. 다른 조합 예시는 [`demo/`](demo/) 폴더 참고.

## 클래스 (6종, id 0-5)

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

## 결과

| 항목 | 값 |
|---|---|
| 모델 | YOLOv8n |
| 입력 해상도 | 640×640 |
| 클래스 수 | 6종 |
| 검증 mAP50 | **0.974** |
| 검증 mAP50-95 | **0.803** |
| 추론 플랫폼 | Jetson Nano (JetPack 4.6, t210ref) |
| 실측 FPS | 초기 5-7fps → 약 1분 후 평균 3.8fps 수준으로 안정화 (대표값 약 3.5-4fps) |
| 웹 UI | FastAPI + WebSocket |

### 검증 결과

| Confusion Matrix | Normalized |
|---|---|
| ![confusion matrix](docs/images/confusion_matrix.png) | ![confusion matrix normalized](docs/images/confusion_matrix_normalized.png) |

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
YOLOv8 학습 (training/train_yolo.py)
    │
    ▼
model/best.pt
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

### 데이터셋 규모

```text
- 총 1,080장
  - Train: 919
  - Validation: 161
- 클래스: 6종
```

---

## 주요 트러블슈팅

### 1. 자동 Bounding Box 라벨링 실패

Otsu Threshold 기반 자동 Bounding Box 검출이 흰 배경+흰 알약처럼 대비가 없는 케이스에서 "성공"으로 표시되면서도 실제로는 배경/이미지 전체를 박스로 잡는 문제가 있었다. 전수 스캔 결과 전체 데이터셋의 약 23%(192장)가 같은 증상이었다.

| 흰 배경 (저대비 — 자동 검출 실패) | 검은 배경 (고대비 — 정상 검출) |
|---|---|
| ![흰 배경 white_caplet](docs/images/white_caplet_white_bg.jpg) | ![검은 배경 white_caplet](docs/images/white_caplet_black_bg.jpg) |

**원인**: contour 면적만 검증하고 실제 라벨로 쓰는 boundingRect 면적은 검증하지 않아서, 그림자로 흩어진 컨투어의 외접 사각형이 이미지 전체를 덮어도 통과했다. 
**해결**: boundingRect 90% 재검증 + 채움비(extent) 0.35 미만 실패 처리 필터를 추가하고, 자동 복구 안 되는 나머지는 수동 라벨링했다.

### 2. 조명 변화에 따른 색상 오분류

검은 배경 촬영본이 카메라 화이트밸런스 보정 때문에 색이 탈색되어, 조명 조건에 따라 흰 알약↔핑크 알약이 서로 오분류되는 문제가 있었다.

| 보정 전 (화이트밸런스로 색 탈색) | 보정 후 (LUT 적용) |
|---|---|
| ![보정 전 pink_caplet](docs/images/pink_orig.jpg) | ![보정 후 pink_caplet](docs/images/pink_fix.jpg) |

**해결**: 클래스별 LUT(밝기+채도만 보정)를 실측 학습해 적용했다. 클래스를 섞어 학습했을 때 평균 오차 2.59/255였던 것을 클래스별로 분리해 0.15-1.3/255까지 줄였다.

### 3. Jetson Nano FPS 저하 원인 분석

`--max-fps 5`(목표 5fps)로 설정해 돌렸는데, 시작 직후엔 5-7fps로 목표를 웃돌다가 약 1분 뒤부터 3.3-4.3fps까지 떨어지는 현상을 발견했다. 우연이 아닌지 확인하기 위해 3회 독립 실행으로 재현 여부를 검증했다.

```
목표(--max-fps)      5 fps
시작 직후            5-7 fps    (목표 근접/상회)
   │
   ▼ (약 1분 경과)
안정화 후            3.3-4.3 fps  (목표 미달, 대표값 약 3.5-4fps)
```

**원인 분석**: 온도는 26→30°C 수준으로 열 스로틀링은 아니었다. GPU 사용률은 버스티하게 움직이는 반면 유휴 구간에도 CPU 한 코어가 꾸준히 점유돼 있어, 병목은 GPU 연산이 아니라 캡처→전처리→인코딩을 순차 처리하는 단일 스레드 구조로 추정된다. (프로파일러로 직접 확인하지 못해 추정 단계 — TensorRT 변환 등 개선 여지는 한계 섹션 참고.)

---

## 성과

- 6종 알약 실시간 탐지 및 복용 정보 제공 시스템 구현
- 검증 mAP50 0.974, mAP50-95 0.803 달성
- Jetson Nano에서 평균 3.5-4 FPS 실시간 추론 검증

## 역할 분담

### 데이터 파이프라인
- Otsu 기반 자동 bbox 생성기 구현 및 검증 필터 추가(`preprocess/auto_label.py`)
- LUT 기반 클래스별 색감 보정 파이프라인 구현(`preprocess/color_fix/`)
- train/val 데이터셋 생성 및 품질 검수(`dataset/`, `data.yaml`)

### 모델 학습·배포
- YOLOv8 학습 파이프라인 구축 및 Jetson Nano 배포(`training/train_yolo.py`)
- FastAPI·WebSocket 기반 실시간 추론 UI 구현(`stream/`)
- 복용 타이밍·복용량·조합 주의 기능 구현

## 한계 및 개선 방향

- 현재 6종 알약만 지원 — 반투명 캡슐(`purple_pill`)은 배경에 따라 색이 크게 달라지는 데이터 일관성 문제로 제외됨
- 단일 카메라·한정된 촬영 환경(조명/배경)에서 수집한 데이터라 일반화에 한계 있음 — `white_caplet`은 색감 보정 후에도 mAP50-95 0.645로 전 클래스 중 최저, 잔여 약점으로 남음
- Jetson Nano에서는 실시간성이 제한적(약 3.5-4fps) — TensorRT 변환이나 더 가벼운 모델로 개선 여지 있음 ([stream/README.md](stream/README.md) 참고, 자동화는 안 돼있음)

---

이 아래부터는 개발자용(설치·재현) 문서다.

---

## 폴더 구조

```
.
├── dataset/              # 학습용 최종 데이터셋 (images/labels train,val + data.yaml)
├── preprocess/           # 라벨링 파이프라인: auto_label.py, split_and_build.py
├── training/             # 학습 코드와 Colab 노트북
│   ├── train_yolo.py
│   └── train_on_colab.ipynb
├── model/
│   └── best.pt           # 학습된 배포 모델 (--export-best로 갱신)
├── stream/               # Jetson Nano 실시간 웹 스트리밍 데모
├── docs/
└── requirements.txt
```

## 설치 (로컬 PC — 전처리/학습용)

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

Jetson Nano(ARM64, JetPack 4.6 · Python 3.6 베이스)는 이 conda 환경을 그대로 쓸 수 없다. Jetson 쪽 세팅은 [실시간 데모](#실시간-데모-jetson-nano) 섹션과 [stream/README.md](stream/README.md) 참고.

## 데이터셋 파이프라인 (전처리/라벨링)

새로 찍은 사진을 클래스별 폴더(`capsule/`, `green_caplet/`, `mint_circle/`, `pink_caplet/`, `white_caplet/`, `yellow_caplet/`)에 넣은 뒤:

```bash
# 1. 자동 bbox 라벨링 (+ 미리보기로 검수)
python preprocess/auto_label.py --input_dir <원본사진폴더> --review
#   _review/ 폴더에서 박스 확인 → 이상한 것만 labelImg 등으로 수동 보정

# 2. train/val 분리 + data.yaml 생성
python preprocess/split_and_build.py --input_dir <원본사진폴더> --output_dir dataset --val_ratio 0.15
```

결과물: `dataset/images/{train,val}/`, `dataset/labels/{train,val}/`, `dataset/data.yaml`.

## 학습

로컬 GPU:

```bash
python training/train_yolo.py --device 0 --export-best
```

`--data`를 안 주면 `dataset/` → `dataset_yolo/` → `dataset_yolo_colab/` 순으로 자동 탐지하고, 학습 전에 라벨/클래스 정합성을 먼저 검사한다. 자세한 옵션은 `python training/train_yolo.py --help` 참고.

Colab(T4 GPU)에서 돌리려면 `training/train_on_colab.ipynb`를 열어서 순서대로 실행하면 된다(저장소를 clone하면 코드와 `dataset/`이 같이 받아짐).

학습이 끝나면 `runs/`에 결과가 저장되고, `--export-best`를 주면 `model/best.pt`로 복사된다.

## 실시간 데모 (Jetson Nano)

학습된 가중치 `model/best.pt`가 저장소에 일반 파일로 포함되어 있어(Git LFS 아님, clone하면 바로 받아짐) 따로 학습하지 않아도 바로 실행할 수 있다.

> Jetson Nano는 JetPack 버전 제약 때문에 `ultralytics`/`opencv-python`을 `requirements.txt`로 그냥 설치하기 어려운 경우가 많다. YOLOv8 추론이 이미 되는 환경이라는 전제로, 여기서 새로 필요한 건 `fastapi`·`uvicorn[standard]`뿐이다 (둘 다 `requirements.txt`에 포함되어 있음). 처음부터 새로 세팅해야 한다면 `stream/README.md`의 Jetson Nano 참고 사항을 먼저 확인한다.

```bash
python stream/server.py
```

Jetson Nano처럼 느린 보드에서는 해상도/전송 프레임을 낮춰서 시작하는 걸 권장한다:

```bash
python3 stream/server.py --width 480 --height 360 --max-fps 5
```

브라우저로 `http://<보드 IP>:8000/` 접속하면 웹캠 영상에 탐지 결과가 얹혀 보인다. Jetson Nano 세팅, 옵션, 성능 관련 참고사항은 `stream/README.md` 참고.

# Troubleshooting

## 1. Otsu 기반 자동 라벨링 실패

### 문제

데이터셋(약 820장)은 `auto_label.py`로 Otsu Threshold 기반 자동 bbox 생성 후 검수하는 방식으로 구축했다.

초기에는 `white_caplet`만 문제인 줄 알았으나, 전체 데이터셋을 재검토한 결과 다른 클래스까지 포함해 약 23%(192장)가 잘못된 bounding box를 가지고 있었다.

대표적인 실패 원인은 두 가지였다.

* 흰 배경 + 흰 알약 → 전경/배경 분리 실패
* 그림자 때문에 컨투어는 작지만 boundingRect가 이미지 대부분을 덮는 경우

  | 흰 배경 (저대비 — 자동 검출 실패) | 검은 배경 (고대비 — 정상 검출) |
  |---|---|
  | ![흰 배경 white_caplet](images/white_caplet_white_bg.jpg) | ![검은 배경 white_caplet](images/white_caplet_black_bg.jpg) |

### 원인

기존 스크립트는

* contour area만 검증
* 실제 라벨로 사용하는 boundingRect는 검증하지 않음

때문에 잘못된 bbox가 정상으로 저장되고 있었다.

### 해결

자동 라벨러를 다음과 같이 수정했다.

* boundingRect 면적 90% 이상 실패 처리
* extent(채움비) 0.35 미만 실패 처리
* GrabCut / HSV 기반 재검출 추가

자동 복구되지 않는 이미지 259장은 수동 라벨링하였다.

### 추가 이슈

labelImg 1.8.6이 PyQt5 5.15에서 float→int 예외로 종료되는 문제를 발견하여 직접 패치하였다.

---

## 2. 웹캠 데이터셋 구축 과정

### 문제

조명 다양성을 확보하기 위해 웹캠 데이터셋을 추가 촬영하였다.

그러나 전역 Otsu Threshold가 배경의 밝기 그라데이션을 객체로 인식하여 모든 클래스에서 bbox가 비정상적으로 생성되었다.

### 해결

median blur 기반 shading correction(`flatten_background()`)을 추가하여 조명 영향을 줄였다.

그래도 완전하지 않아 모든 이미지를 수동 검수하였다.

추가로 labelImg 사용 중 발견한 문제도 함께 수정하였다.

* float→int crash
* classes.txt 관리 문제
* Auto Save 경로 오류
* 클래스 인덱스 병합 문제

병합 과정에서는 MD5 검사를 이용하여 중복 데이터를 제거하였다.

---

## 3. 조명에 따른 색상 변화

### 문제

검은 배경에서 촬영한 이미지가 카메라 화이트밸런스 영향으로 탈색되어

* white ↔ pink

오분류가 발생하였다.

  | 보정 전 (화이트밸런스로 색 탈색) | 보정 후 (LUT 적용) |
  |---|---|
  | ![보정 전 pink_caplet](images/pink_orig.jpg) | ![보정 후 pink_caplet](images/pink_fix.jpg) |

### 해결

클래스별 LUT를 생성하여 색감을 보정하였다.

초기에는 RGB 채널별 LUT를 적용했지만 배경까지 변색되는 문제가 발생하여

* 밝기(L)
* 채도(S)

만 보정하는 방식으로 변경하였다.

클래스를 통합해 LUT를 만들 경우 평균 오차가 2.59였으나,

클래스별 LUT 적용 후 0.15~1.3 수준으로 감소하였다.

기존 검은 배경 촬영본 403장 전체에 동일하게 적용하였다.

---

## 4. purple_pill 클래스 제거

### 문제

반투명 캡슐 특성상

* 흰 배경
* 검은 배경

에서 서로 다른 색으로 촬영되었다.

이는 라벨 수정으로 해결 가능한 문제가 아니라 데이터 자체의 일관성 문제였다.

  | 흰 배경 | 검은 배경 |
  |---|---|
  | ![흰 배경](images/purple_pill_white_bg.jpg) | ![검은 배경](images/purple_pill_black_bg.jpg) |

### 해결

해당 클래스를 데이터셋에서 제외하였다.

재도입하려면 동일 조명·동일 배경 조건으로 재촬영이 필요하다.

---

# Validation

## 데이터셋 무결성

최종 데이터셋에 대해 자동 검사를 수행하였다.

* 클래스 수 검증
* bbox 형식 검증
* 좌표 범위 검증
* auto_label 실패 패턴 재검사
* negative label 규칙 확인
* train/val MD5 중복 검사

모든 항목을 통과하였다.

---

## 모델 재현성

* preflight() 검사 결과 동일
* validation 재실행 결과 동일
* Jetson / Local best.pt MD5 동일

학습 결과와 Jetson 배포 모델이 동일함을 확인하였다.

---

# Result

## Validation Result

`yolo val model=model/best.pt data=dataset/data.yaml imgsz=640` (GTX 1660, val 161장)

전체: precision 0.934 / recall 0.973 / **mAP50 0.974 / mAP50-95 0.803**, 추론 5.0ms/image

| 클래스 | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|
| capsule | 0.923 | 1.000 | 0.995 | 0.821 |
| green_caplet | 0.950 | 1.000 | 0.995 | 0.870 |
| mint_circle | 0.934 | 0.960 | 0.929 | 0.788 |
| pink_caplet | 0.961 | 1.000 | 0.995 | 0.831 |
| white_caplet | 0.960 | 0.889 | 0.947 | 0.645 |
| yellow_caplet | 0.874 | 0.990 | 0.985 | 0.865 |

`white_caplet`이 recall·mAP50-95 최하위 — 3번(색감 보정) 이후에도 남은 잔여 약점.

| Confusion Matrix | Normalized |
|---|---|
| ![confusion matrix](images/confusion_matrix.png) | ![confusion matrix normalized](images/confusion_matrix_normalized.png) |

---

## Jetson Nano Performance

* 시작 직후 : 5~7 FPS
* 안정화 후 : 3.3~4.3 FPS
* 대표값 : 약 3.5~4 FPS

온도는 26→30°C로 유지되어 열 스로틀링은 발생하지 않았다.

GPU는 버스티하게 동작하고 CPU 한 코어가 지속적으로 사용되어, 당시에는 병목을
capture → preprocessing → encoding의 단일 스레드 처리로 추정했다. 아래 후속
계측에서 실제 지배 구간은 inference와 draw로 구체화했다.

> 이 저하는 당시 `.107` 보드와 기존 SD카드 조합에서만 관찰됐다. 이후 검증된
> `.108` SD카드를 `.107` 보드에 꽂은 카드 스왑 테스트에서는 6.2~6.5 FPS로
> 안정적이어서 보드 고유 하드웨어 결함 가설은 배제했다. 기존 카드는 초기화되어
> 당시 파일시스템·백그라운드 프로세스·전원 상태 중 세부 원인은 확정할 수 없다.

---

## Jetson Nano Controlled Optimization (2026-08-13)

카메라 장면을 MJPEG AVI(640×480, 900프레임)로 고정하고, 서버 입력은 480×360,
warm-up 30초, 실행 180초, 브라우저 WebSocket 연결 상태로 통일했다. 각 최종 비교는
3회 반복했고 CSV에는 프레임별 단계 시간과 검출 수를 기록했다.

| 경로 | 반복 | FPS | inference 평균 | draw 평균 | total 평균 | total P95 |
|---|---:|---:|---:|---:|---:|---:|
| PyTorch + 기본 한글 draw | 3 | 6.34 | 63.14ms | 69.44ms | 157.71ms | 163.83ms |
| PyTorch + draw 생략(격리 실험) | 1 | 11.51 | 62.55ms | 0ms | 86.89ms | 89.34ms |
| TensorRT FP16 + 기본 한글 draw | 3 | 7.41 | 46.28ms | 62.90ms | 135.01ms | 159.12ms |
| TensorRT FP16 + OpenCV fast draw | 3 | **13.77** | **46.26ms** | **1.12ms** | **72.65ms** | **74.02ms** |

TensorRT FP16만 적용하면 순수 inference가 26.7%, 전체 시간이 14.4% 감소했다.
추론 개선 후에는 기본 `result.plot()`이 가장 큰 병목이 됐다. 한글 라벨 때문에
사용되는 PIL 기반 렌더링 대신 OpenCV로 bbox·신뢰도·짧은 영문 라벨을 그리는 선택형
`--fast-draw`를 추가하자 draw가 69.44ms에서 1.12ms로 줄었다. 조합·복용량 등
웹 UI의 한글 메시지와 검출 집계 이름은 그대로 유지한다.

최종 경로는 기준선 대비 total latency 53.9% 감소, 처리율 2.17배 증가다. 세 실행의
total 평균은 72.71/72.66/72.56ms로 재현됐고 GPU 최고 온도는 32°C였다.
`capture_ms`는 평균 2.86ms에 불과해 처리량의 병목이 아니므로 캡처/추론 스레드 추가
분리는 이번 범위에서 생략했다.

### 정확도 비교 조건

고정 shape TensorRT 엔진은 640×640 square 입력을 사용한다. 최초 PyTorch validation의
직사각형 배치(`rect=True`) 결과와 직접 비교하면 전처리 조건이 달라 오해가 생기므로,
두 backend 모두 `imgsz=640`, `batch=1`, `rect=False`로 맞췄다.

| Backend | mAP50 | mAP50-95 |
|---|---:|---:|
| PyTorch FP32, square | 0.96046 | 0.68069 |
| TensorRT FP16, square | 0.96073 | 0.68150 |

161장/158개 객체 validation에서 FP16 정확도는 동일 조건 PyTorch 대비 오차 범위 내
유지됐다. 기존의 더 높은 `rect=True` 수치(0.97603/0.81132)는 입력 정책이 다르므로
TensorRT 변환 전후 표에는 사용하지 않는다.

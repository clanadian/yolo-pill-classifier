# 진행 상황 (2026-07-27)

## 완료
- **레거시 파일 제거**: 가위바위보 Teachable Machine 잔재 파일 삭제
  (`1_dataset.py`, `2_train.py`, `3_1_featureMapVis.py`, `3_2_filterVis.py`, `4_predict_testset.py`, `labels.txt`)
- **역할 폴더 분리**
  - `전처리/` — `auto_label.py`(자동 bbox 라벨링), `split_and_build.py`(train/val 분리 + data.yaml 생성) → 내 담당
  - `train/` — `train_yolo.py`(빈 파일, 팀원이 채울 실제 학습 스크립트) → 팀원 담당
- **클래스 정리**: `auto_label.py` / `split_and_build.py`의 클래스 목록을 실제 `dataset/` 폴더명 기준으로 통일
  `capsule, green_caplet, mint_circle, pink_caplet, white_caplet, yellow_caplet` (id 0~5)
- **데이터셋 파일명 정리**: 날짜 기반 파일명 → 클래스별 `000.jpg`부터 순번으로 재정렬 (촬영 순서 유지)
- **현재 데이터 수량**: capsule 109 / green_caplet 148 / mint_circle 129 / pink_caplet 146 / white_caplet 141 / yellow_caplet 147 (총 820장)
- **`auto_label.py` 실행 + 검수**: 전체 820장 자동 bbox 라벨링. `white_caplet`은 촬영 배경이 중간에 바뀐 걸 발견
  (000~067번 흰 배경은 저대비로 박스가 엉뚱하게 잡힘 / 068~140번 검은 원단 배경은 정상)
- **`white_caplet` 000~067번(68장) 수동 라벨링**: 흰 배경 저대비 구간은 자동 검출 신뢰 불가라 직접 사진 보고 bbox 좌표 추정해서 라벨 교체. 068~140번(검은 배경)은 자동 라벨 그대로 사용. 검증 결과 전체 141장 중 이상 박스(면적 50% 초과) 0건
- **`split_and_build.py` 실행** → `dataset_yolo/` 생성 (val_ratio 0.15)

  | 클래스 | train | val |
  |---|---|---|
  | capsule | 93 | 16 |
  | green_caplet | 126 | 22 |
  | mint_circle | 110 | 19 |
  | pink_caplet | 124 | 22 |
  | white_caplet | 120 | 21 |
  | yellow_caplet | 125 | 22 |

- **`dataset.zip` 생성** (원본 `dataset/` 폴더, 라벨 `.txt` 포함, 1.8GB) → 구글 드라이브로 팀원에게 공유 예정
- **공유 방식 결정**: `dataset_yolo/`(456MB, 학습 즉시 가능한 최종 구조)는 용량이 작아 그냥 git push. 원본 `dataset/`(1.8GB, 사진 원본)은 git에 올리기엔 커서 `dataset.zip`으로 구글 드라이브 공유

## 알아둘 점 (팀원에게 전달 시 주의)
- `dataset_yolo/data.yaml`의 `path:` 값이 지금 이 컴퓨터의 절대경로(`/home/adas/yolo-pill-classifier/dataset_yolo`)로 박혀 있음. git push해서 팀원이 다른 경로에 클론하면 그 값 그대로는 안 맞을 수 있으니, 팀원이 받은 뒤 자기 환경 경로로 고쳐야 함 (또는 학습 스크립트에서 `path`를 상대경로/런타임 경로로 재계산하도록 처리)

## 다음 할 일 (내 쪽 — 전처리)
- [x] `전처리/auto_label.py` 실행 → bbox 자동 라벨링, 검수
- [x] 라벨 실패/이상 이미지 수동 확인·보정 (white_caplet 68장)
- [x] `전처리/split_and_build.py` 실행 → `images/train,val` + `labels/train,val` + `data.yaml` 생성
- [x] 결과물 공유 준비 (`dataset_yolo` git push 예정, `dataset.zip` 구글 드라이브 공유 예정)

## 다음 할 일 (팀원 쪽 — 학습)
- [ ] `data.yaml`의 `path` 경로를 자기 환경에 맞게 확인/수정
- [ ] `train/train_yolo.py`에 실제 YOLOv8 학습 코드 작성 (`data.yaml` 받은 뒤)
- [ ] 학습 후 `best.pt` 생성 → `yolov8_cam.py`로 웹캠 데모 검증

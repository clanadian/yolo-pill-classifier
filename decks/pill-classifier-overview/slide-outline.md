# YOLOv8 알약 인식 & Jetson Nano 실시간 데모

## Meta

- **Topic**: YOLOv8 기반 알약 6종 탐지 프로젝트 — 개요·기대효과, 개발 과정에서 겪은 트러블슈팅, 실제 데모 결과, 고찰 순으로 구성
- **Target Audience**: 팀/수업 발표 (기술적 배경이 있는 청중 가정)
- **Tone/Mood**: 차분하고 신뢰감 있는 톤, 트러블슈팅 파트는 증상-원인-조치 구조로 구체적이고 담백하게, 결과 파트는 실제 스크린샷으로 증명
- **Slide Count**: 18 slides
- **Aspect Ratio**: 16:9
- **style**: swiss-international-style (Pure white `#FFFFFF` 배경 — 사용자 요청에 따른 화이트 테마)
- **mode**: html

## Slide Composition

### Slide 1 - Cover

- **Type**: Cover
- **Title**: YOLOv8 알약 인식 프로젝트
- **Subtitle**: 개요 · 트러블슈팅 · 결과 · 고찰

### Slide 2 - Table of Contents

- **Type**: Contents
- **Items**:
  1. 개요 (프로젝트 목표 / 데이터셋 / 학습 / Jetson 실시간 데모 / 안내 기능 / 기대효과)
  2. 트러블슈팅 (자동 라벨링 · 데이터 일관성 · 색보정)
  3. 결과 (실제 Jetson Nano 데모 화면)
  4. 고찰 (배운 점 · 한계 · 다음 단계)

### Slide 3 - [개요] 프로젝트 목표

- **Type**: Content
- **Key Message**: 알약 6종을 실시간으로 탐지하고 Jetson Nano에서 바로 웹으로 확인하는 데모까지 구축
- **Details**:
  - 파이프라인: 사진 촬영 → 데이터셋 구축 → YOLOv8 학습 → Jetson Nano 실시간 웹 데모
  - 탐지 클래스 6종: capsule, green_caplet, mint_circle, pink_caplet, white_caplet, yellow_caplet
  - 데모 화면에서는 클래스명을 영양제 이름(오메가3/마그네슘/유산균/칼슘/비타민C/비타민D)으로 표시

### Slide 4 - [개요] 데이터셋 & 학습

- **Type**: Statistics
- **Key Message**: 6클래스 + 네거티브 샘플까지 총 1,080장 규모, 로컬/Colab 양쪽에서 학습 가능
- **Details**:
  - 클래스별 장수: capsule 149 / green_caplet 188 / mint_circle 169 / pink_caplet 186 / white_caplet 181 / yellow_caplet 187
  - 배경만 있는 네거티브 샘플 20장(오탐지 감소 목적), 최종 train 919 / val 161
  - `train/train_yolo.py`(로컬) · `notebooks/train_on_colab.ipynb`(Colab T4) · `--export-best`로 `weights/best.pt` 자동 생성

### Slide 5 - [개요] Jetson Nano 실시간 데모

- **Type**: Content
- **Key Message**: 카메라 캡처·추론·웹서버를 Jetson Nano 한 대에서 전부 처리하는 LAN 전용 실시간 데모
- **Details**:
  - USB 웹캠 → YOLOv8 추론(별도 스레드) → bbox/라벨 오버레이 → WebSocket 스트리밍
  - `FrameBroadcaster`가 최신 프레임 1장만 보관해 느린 보드에서도 지연 누적 없이 항상 최신 프레임 표시
  - 브라우저에서 `http://<Jetson IP>:8000/` 접속만으로 확인 (LAN 전용, 포트포워딩/HTTPS 불필요)
  - 실제 인식 화면은 뒤 [결과] 섹션에서 스크린샷으로 확인

### Slide 6 - [개요] 조합/타이밍/복용량 안내 기능

- **Type**: Content
- **Key Message**: 감지 결과에 사용자가 미리 등록한 규칙을 매칭해 안내 배너 표시 (모델의 의학적 판단 아님)
- **Details**:
  - 조합 배너(`combos.json`): 좋은 조합(비타민D+칼슘 등) / 확인 필요 조합(칼슘+마그네슘 등)
  - 복용 타이밍(`timing.json`): "오메가3는 식사와 함께" 등 클래스별 안내
  - 복용량(`dosage.json`): 권장 개수 초과 감지 시 "칼슘 3개 감지됨 — 한 번엔 2알만" 자동 생성
  - 실제 동작 화면은 뒤 [결과] 섹션에서 스크린샷으로 확인

### Slide 7 - [개요] 기대효과

- **Type**: Content
- **Key Message**: 단순 탐지를 넘어, 실제 임베디드 환경에서 동작하는 "안내형" 서비스 구조를 검증
- **Details**:
  - 실용적 가치: 여러 영양제를 동시에 놓고 봐도 각각 무엇인지, 언제·몇 알 먹어야 하는지 한눈에 확인 가능
  - 기술적 가치: 데이터 수집부터 학습, 임베디드 보드(Jetson Nano) 실시간 추론·웹 스트리밍까지 엔드투엔드 파이프라인을 직접 구현
  - 안전한 설계 패턴: 모델이 직접 판단하지 않고 사용자가 등록한 규칙만 매칭하는 구조 — 향후 실제 의약품 DB(예: 식약처 의약품안전나라 API) 연동 시에도 그대로 재사용 가능한 뼈대
  - 확장 가능성: 클래스를 실제 성분 인식 모델로 교체하면 복약 관리 보조 도구로 확장 여지

### Slide 8 - [트러블슈팅] Section Divider

- **Type**: Section Divider
- **Title**: 트러블슈팅
- **Subtitle**: 데이터 라벨링부터 실제 배포까지, 단계마다 만난 문제와 해결 과정

### Slide 9 - [트러블슈팅 1] 자동 라벨링의 함정

- **Type**: Content
- **Key Message**: "콘솔은 성공, 실제 박스는 배경 전체" — 조용히 실패하는 자동화의 위험
- **Details**:
  - 증상: `auto_label.py`(Otsu 임계값 기반)가 성공으로 표시했지만 실제로는 820장 중 192장(23%)에서 박스가 이미지 전체를 덮음
  - 원인: ① 배경·알약이 둘 다 흰색이면 Otsu가 전경/배경을 구분 못함(white_caplet) ② 컨투어 면적만 검증하고 실제 라벨에 쓰는 boundingRect는 검증 안 함
  - 조치: boundingRect 90% 재검증 + 컨투어 채움비 0.35 미만 필터 추가, 그래도 못 건진 259장은 수동 라벨링

### Slide 10 - [트러블슈팅 2] 데이터 일관성 문제

- **Type**: Content
- **Key Message**: 라벨을 다시 그려도 못 고치는 문제는 과감히 제외
- **Details**:
  - 증상: `purple_pill`(반투명 캡슐)이 촬영 배경(흰/검)에 따라 완전히 다른 색으로 촬영됨
  - 판단: 라벨링 문제가 아니라 촬영 조건 자체의 데이터 일관성 문제로 진단
  - 조치: 해당 클래스를 데이터셋에서 통째로 제외, 재도입하려면 배경 조건을 통일한 재촬영 필요

### Slide 11 - [트러블슈팅 3] 조명에 따른 색 오분류

- **Type**: Content
- **Key Message**: 채널별 보정은 배경까지 오염시켜 실패 → 휘도/채도만 분리 보정하는 방식으로 재설계
- **Details**:
  - 증상: 조명이 약하면 흰 알약이 핑크로, 특정 조건에선 핑크가 흰색으로 오분류(white_caplet ↔ pink_caplet)
  - 원인: 검은 배경 촬영본이 카메라 화이트밸런스 보정으로 색이 탈색되어 보임
  - 1차 시도 실패: B/G/R 채널 독립 학습 → 배경까지 색조가 오염되는 부작용 발견
  - 재설계: 휘도(밝기) + 채도(HSV S채널)만 따로 학습하는 LUT 방식(`preprocess/color_fix/`)으로 전환
  - 결과: 클래스 섞어 학습 시 오차 2.59/255 → 클래스별 개별 학습 시 0.15~1.3/255로 개선, 6클래스 403장 전체 동일 적용

### Slide 12 - [결과] Section Divider

- **Type**: Section Divider
- **Title**: 결과
- **Subtitle**: 실제 Jetson Nano에서 촬영한 라이브 데모 화면

### Slide 13 - [결과 1] 클래스별 인식 결과

- **Type**: Content (이미지 그리드, 2x3 또는 3x2)
- **Key Message**: 6개 클래스 모두 실시간으로 정확히 인식되고, 화면에는 영양제 이름으로 표시됨
- **Details / 이미지**:
  - `demo/capsule_오메가3_1.png` — capsule → 오메가3
  - `demo/green_caplet_마그네슘_1.png` — green_caplet → 마그네슘
  - `demo/mint_circle_유산균_1.png` — mint_circle → 유산균
  - `demo/pink_caplet_칼슘.png` — pink_caplet → 칼슘
  - `demo/white_caplet_비타민C_1.png` — white_caplet → 비타민C
  - `demo/yellow_caplet_비타민D_1.png` — yellow_caplet → 비타민D

### Slide 14 - [결과 2] 다중 인식 & 조합 안내 결과

- **Type**: Content (이미지 그리드)
- **Key Message**: 여러 알약을 동시에 비춰도 각각 인식하고, 조합 규칙이 맞으면 배너로 안내
- **Details / 이미지**:
  - `demo/all.png`, `demo/all_2.png` — 여러 알약 동시 인식(다중 bbox)
  - `demo/비타민D_칼슘.png` — 좋은 조합 배너 예시("비타민D가 칼슘 흡수를 도와줘요")
  - `demo/칼슘_마그네슘.png` — 확인 필요 조합 배너 예시("흡수 경로를 나눠 써요")
  - `demo/비타민D_오메가3.png`, `demo/비타민D_마그네슘.png`, `demo/비타민C_유산균.png` — 추가 조합 예시(디자인 단계에서 지면에 맞춰 일부만 선택 가능)

### Slide 15 - [결과 3] 복용량 안내 결과

- **Type**: Content
- **Key Message**: 같은 종류가 권장 개수보다 많이 잡히면 실제 개수를 반영한 경고가 즉석에서 생성됨
- **Details / 이미지**:
  - `demo/all_3_한번에_한_알.png`, `demo/all_3_한번에_한_알_2.png` — 권장량 초과 감지 시 "한 번엔 N알만 드세요" 안내 화면

### Slide 16 - [고찰] Section Divider

- **Type**: Section Divider
- **Title**: 고찰
- **Subtitle**: 이번 프로젝트에서 배운 것과 남은 한계

### Slide 17 - [고찰] 배운 점과 한계

- **Type**: Content
- **Key Message**: 자동화는 "성공 로그"가 아니라 실제 결과값을 검증해야 신뢰할 수 있다
- **Details**:
  - 자동 라벨링·자동 검증 모두 "에러 없음"이 곧 "정확함"을 보장하지 않음 — 실제 박스 좌표, 실제 색상 오차 수치를 직접 확인하는 과정이 반복적으로 필요했음
  - 데이터 품질(조명, 배경, 색보정)이 모델 성능에 미치는 영향이 모델 구조보다 컸음
  - 로컬 개발 환경과 실제 배포 보드(Jetson)의 라이브러리 버전 차이에서만 드러나는 문제가 있었음(예: model.names 이슈) — 실기기 테스트가 필수적
  - 한계: 탐지 클래스는 색상/모양 기반이라 실제 성분을 특정하지 못함. 조합/타이밍/복용량 안내는 사용자가 등록한 규칙일 뿐 의학적 판단이 아니며, 화면에 "참고용 데모" 문구를 상시 노출해 명확히 함

### Slide 18 - 마무리

- **Type**: Closing
- **Message**: 데이터셋 구축부터 실시간 데모까지 — 각 단계의 문제를 원인부터 추적해 해결한 과정을 통해 완성한 파이프라인. Q&A

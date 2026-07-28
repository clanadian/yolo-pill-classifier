# 알약 조합 안내 배너 기획 (2026-07-28)

## 배경

`stream/server.py`는 지금 웹캠+YOLO 탐지 결과를 bbox/라벨이 그려진 JPEG 프레임으로만
브라우저에 스트리밍한다. 탐지된 클래스 이름 자체는 서버 안에서 버려지고 클라이언트로
전달되지 않는다.

여기에 "이 조합은 아침에 같이 드세요" / "이 조합은 확인이 필요합니다" 같은 안내 배너를
추가하려 한다. 다만 `dataset/data.yaml`의 클래스는 실제 약 성분이 아니라 색상/모양 기반
(`capsule`, `pink_caplet` 등)이므로, 모델이 스스로 약물 상호작용을 추론하는 것처럼
보이면 안 된다. 그래서 이 기능은 **모델이 인식한 클래스 조합에 대해, 사용자가 미리
등록해둔 문구를 보여주는 순수 룰 매칭 기능**으로 한정한다. 진짜 의약품 데이터베이스나
실제 상호작용 판단 로직은 이번 범위에 포함하지 않는다.

## 접근 방식

1. **룰 파일** — `stream/combos.json`에 사람이 직접 편집하는 배열.
   각 항목: `{"classes": [...], "type": "good"|"caution", "message": "..."}`.
   `classes`에 있는 클래스가 모두 현재 감지 목록에 포함되면(subset 매칭) 발동.
   여러 룰이 동시에 맞으면 `caution`을 우선 노출(안전 쪽을 숨기지 않기 위해),
   없으면 첫 번째로 매칭된 `good` 룰을 노출한다.
   - 파일이 없으면 경고 로그만 남기고 빈 룰 목록으로 서버는 정상 구동
     (기능은 꺼진 상태).
   - 예시 항목 2개는 실제 클래스 이름으로 채우되, 메시지에
     "(예시 — 직접 수정하세요)"를 붙여 실제 조언으로 오인하지 않게 한다.

2. **`stream/detector.py`** — `infer_and_annotate`가 감지된 클래스 이름 집합도
   함께 반환하도록 변경 (`model.names` + `results[0].boxes.cls` 사용).
   이 함수는 `stream/server.py`에서만 쓰이므로 반환 시그니처를 자유롭게 바꿔도
   다른 곳이 깨지지 않는다.

3. **`stream/server.py`**
   - 순수 함수 `match_combo(detected_classes: set[str], rules: list) -> dict | None`
     추가 — 카메라 없이도 바로 손으로 검증 가능.
   - `FrameBroadcaster`가 JPEG bytes 외에 현재 배너 상태도 같이 들고 있도록 확장.
   - `capture_loop`에서 매 프레임 추론 후 감지 클래스 집합을 계산하고 `match_combo`로
     판정. 탐지가 프레임마다 깜빡이는 걸 완화하기 위해, 매칭이 사라져도 최근
     약 1.5초 이내면 계속 보여주는 유예시간(hold) 로직을 `time.monotonic()` 기반으로
     둔다 (기존 fps 로깅과 같은 스타일).
   - `/ws` 엔드포인트: 기존 바이너리 JPEG 프레임에 더해, 배너 상태가 바뀔 때만
     텍스트(JSON) 프레임을 추가로 보낸다. 연결 하나로 이미지+배너를 함께 보내
     별도 WebSocket 연결을 늘리지 않는다.

4. **`stream/static/index.html` / `app.js`**
   - 항상 보이는 고정 문구 추가: "⚠ 참고용 데모입니다 — 실제 복약 판단에
     사용하지 마세요."
   - 배너 영역(`#combo-banner`): `good`이면 녹색, `caution`이면 빨강/주황,
     매칭 없으면 숨김.
   - `app.js`의 `ws.onmessage`에서 문자열(JSON)이면 배너 갱신, 바이너리면
     기존처럼 이미지 처리.

5. **`stream/README.md`** — `combos.json` 스키마, 우선순위 규칙, "직접 채워야
   하는 예시 파일"이라는 점을 문서화.

## 변경 파일 요약

- `stream/detector.py` — 클래스 이름 추출 추가
- `stream/server.py` — 룰 로딩, `match_combo`, hold 로직, `/ws`에서 JSON 전송
- `stream/static/index.html` — 배너 영역 + 고정 디스클레이머
- `stream/static/app.js` — 텍스트/바이너리 메시지 분기 처리
- `stream/combos.json` (신규) — 예시 룰 파일
- `stream/README.md` — 사용법 문서 추가

## 검증 방법

1. **순수 함수 검증**: `match_combo({"pink_caplet", "white_caplet"}, rules)` 등
   여러 클래스 조합을 넣어 good/caution/None 판정이 룰 파일과 일치하는지 확인
   (카메라 불필요).
2. **서버 구동 검증**: `python stream/server.py --source <웹캠 또는 테스트 영상
   경로>` 실행 후 브라우저에서 `http://localhost:8000/` 접속, 콘솔 로그
   (`inference fps`)로 정상 동작 확인.
3. **실제 배너 확인**: `combos.json` 예시 조합에 해당하는 물체(또는 테스트 영상)를
   카메라에 비춰 배너가 뜨는지, 물체를 치웠을 때 유예시간 후 배너가 사라지는지
   확인.
4. **연결 안정성**: 배너가 없을 때 `#combo-banner`가 완전히 숨겨지는지, 페이지
   새로고침/재연결 시에도 정상 동작하는지 확인.

# 무료 SNS 기반 특가 감지 에이전트

AI 구독/소프트웨어와 Apple 제품 특가 후보를 보수적으로 점수화하고, 신규 후보만 Telegram으로 보내는 Python 3.12 프로젝트입니다.

## 무료 운영 방식

- 기본 구현은 유료 API, 유료 프록시, 유료 크롤링 서비스를 사용하지 않습니다.
- X와 Threads는 v1의 중심 provider로 구조만 마련되어 있지만, 무료/공식/약관 준수 public search/read 접근이 없으므로 기본 비활성화되어 있습니다.
- 로그인 쿠키 스크래핑, CAPTCHA 우회, 우회 프록시, 무단 대량 크롤링은 구현하지 않습니다.
- 사용자가 약관상 읽을 수 있는 공식 HTTPS JSON 피드가 있으면 `DEAL_ALERT_JSON_FEED_URLS`에 쉼표로 추가할 수 있습니다. 각 item은 `id`, `source`, `url`, `author`, `text`, `created_at` 필드를 사용합니다.

## GitHub Actions 5분 주기

`.github/workflows/check-deals.yml`은 다음 schedule로 실행됩니다.

```yaml
cron: "*/5 * * * *"
```

GitHub Actions schedule은 정확히 5분마다 실행된다는 보장이 없고, GitHub 부하나 저장소 상태에 따라 지연되거나 일부 실행이 누락될 수 있습니다. 공개 저장소의 무료 GitHub Actions 실행을 기본 전제로 합니다.

실행 후 `state/seen.json`이 바뀌면 workflow가 변경된 state를 커밋합니다. 한 번 알림을 보낸 URL 또는 post id는 신규 후보가 아니므로 다시 보내지 않으며, 따라서 같은 항목의 24시간 이내 재알림도 발생하지 않습니다.

## Telegram 설정

GitHub 저장소 Secrets에 다음 값을 등록합니다.

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

선택적으로 Repository Variables에 다음 값을 조정할 수 있습니다.

- `MIN_SCORE`: 기본값 `8`
- `VIRAL_THRESHOLD`: 기본값 `7`
- `DEAL_ALERT_JSON_FEED_URLS`: 허용된 HTTPS JSON feed URL 목록

로컬에서는 `.env.example`을 참고해 환경변수를 설정한 뒤 실행합니다.

```powershell
python -m pip install -e .[dev]
python -m deal_alert.main --dry-run
```

## 감지 기준

관심 상품 키워드가 없는 글은 v1에서 알림하지 않습니다.

AI 키워드:

- `ChatGPT Pro`, `GPT Pro`, `ChatGPT Plus`, `Claude`, `Claude Pro`, `Gemini`, `Perplexity`, `Cursor`, `Copilot`, `Midjourney`, `Notion AI`

Apple 키워드:

- `아이패드`, `iPad`, `iPad Pro`, `MacBook`, `맥북`, `AirPods`, `에어팟`, `Apple Watch`, `iPhone`, `애플펜슬`

특가 신호:

- `오가격`, `역대가`, `대란`, `실수`, `품절`, `쿠폰`, `반값`, `무료`, `할인`, `핫딜`, `특가`, `카카오톡 선물하기`, `쿠팡`

Apple 후보는 특가 점수 `>= MIN_SCORE`이면 알림 대상입니다. AI 후보는 특가 점수 `>= MIN_SCORE`이고 바이럴 점수 `< VIRAL_THRESHOLD`이며 차단 사유가 없어야 합니다.

## 키워드/점수 조정

- 상품 키워드, 특가 신호, 광고/바이럴 감점 키워드, AI 구독 위험 패턴은 `src/deal_alert/detector.py`의 상수 목록에서 조정합니다.
- `MIN_SCORE`를 높이면 알림이 줄고, 낮추면 알림이 늘어납니다.
- `VIRAL_THRESHOLD`를 낮추면 AI 구독/소프트웨어 글이 더 엄격하게 차단됩니다.
- 기본값은 보수적인 운영을 위해 `MIN_SCORE=8`, `VIRAL_THRESHOLD=7`입니다.

## 광고/바이럴/사기 필터

다음 표현은 강하게 감점합니다.

- `광고`, `협찬`, `제휴`, `파트너스`, `쿠팡파트너스`, `추천코드`, `레퍼럴`, `초대코드`, `체험단`, `공구`, `댓글 링크`, `프로필 링크`, `DM`, `카톡 문의`, `오픈채팅`

`광고 아님`, `제휴 아님`처럼 부정하는 표현은 광고 표현으로 오판하지 않도록 먼저 제거합니다.

AI 구독권은 Apple 하드웨어보다 더 보수적으로 처리합니다. `평생 이용권`, `무제한`, `계정 공유`, `대리 결제`, `우회 결제`, `VPN`, `터키`, `아르헨티나`, `인도 우회`, `월 몇천원`, `공식보다 싸게` 같은 패턴은 차단 사유가 됩니다. AI 구독권은 공식/검증 판매처 URL이 없으면 기본 차단하며, 공식가 대비 70% 이상 저렴한 가격은 `사기/바이럴 의심`으로 분류하고 Telegram으로 보내지 않습니다.

## 수동 실행

```powershell
python -m deal_alert.main --dry-run
```

`--dry-run`은 Telegram 전송과 state 저장 없이 provider 실행, 점수화, 차단/알림 판단을 확인합니다.

## 테스트

```powershell
python -m pip install -e .[dev]
pytest
```

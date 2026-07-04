# K-Bridge 문서 챗봇 (Ask K-Bridge) — UI 디자인 스펙

> 대상: `KBridgeProject` 학생용 모바일 앱(React + Vite, 순수 CSS)의 신규 화면.
> 롤플레잉 게임과 별개인 **문서 기반 RAG 챗봇** — 학생이 생활/학사/비자 등 등록된 문서에 대해
> 질문하면, 문서 검색 결과를 근거로 답변하고 **한국어 원문 / English 번역을 병기**해서 보여준다.
> 이 문서는 Claude Design(design-sync)용 컴포넌트 사양서다.

---

## 1. 제품 컨텍스트

- 사용자: 필리핀 까비떼 다스마리냐스 예일 국제 문화원의 10대 후반~20대 초반 학습자.
- 앱 기본 언어는 **영어(EN)**, 시스템 언어는 EN/KO 토글 가능.
- 챗봇의 답변 본문과 RAG 근거 문서는 **KO 원문 + EN 번역 병기**가 핵심 요구사항.
  - 이유: 학습자는 한국어를 배우는 중이므로 원문(KO)이 학습 자료이고, EN이 이해 보조.
- 프론트는 모바일 앱처럼 보이는 React SPA. 최대 콘텐츠 폭 ~430px 프레임 안에서 동작.
- 기존 화면(GameMainPage, DashboardMainPage)과 같은 비주얼 시스템을 유지한다.

## 2. 디자인 토큰 (기존 AGENTS.md 준수 + 챗봇 확장)

### 2.1 색상 — 기존 토큰 (변경 금지)

| Token | HEX | 사용 위치 |
|---|---|---|
| `--color-background` | `#FAF7F0` | 전체 배경 |
| `--color-primary` | `#336B8E` | 주요 버튼, 사용자 말풍선, 활성 상태 |
| `--color-learning` | `#F2C94C` | 주의/하이라이트 (KO 원문 라벨 배지) |
| `--color-success` | `#6FCF97` | 완료·성공 상태 |
| `--color-text` | `#2D3748` | 본문 텍스트 |
| `--color-muted` | `#718096` | 보조 텍스트, 타임스탬프 |
| `--color-card` | `#FFFFFF` | 카드·말풍선 배경 |
| `--color-border` | `#E2E8F0` | 구분선, 카드 테두리 |

### 2.2 챗봇 전용 확장 토큰 (신규 제안)

| Token | 값 | 사용 위치 |
|---|---|---|
| `--chat-user-bubble` | `#336B8E` (primary) | 사용자 말풍선 배경 |
| `--chat-user-text` | `#FFFFFF` | 사용자 말풍선 텍스트 |
| `--chat-bot-bubble` | `#FFFFFF` (card) | 봇 말풍선 배경 |
| `--chat-ko-accent` | `#336B8E` | KO 원문 세로 악센트 바 |
| `--chat-en-accent` | `#6FCF97` | EN 번역 세로 악센트 바 |
| `--chat-ref-bg` | `#F5F9FB` | RAG 근거 카드 배경 (primary 5% 틴트) |
| `--chat-score-high` | `#6FCF97` | 유사도 높음 배지 (score ≥ 0.8) |
| `--chat-score-mid` | `#F2C94C` | 유사도 중간 배지 (0.6–0.8) |
| `--chat-score-low` | `#718096` | 유사도 낮음 배지 (< 0.6) |

### 2.3 타이포그래피

- 폰트: 시스템 스택 (`-apple-system, "Segoe UI", Roboto, "Noto Sans KR", sans-serif`).
  KO/EN 혼용이 많으므로 Noto Sans KR 폴백 필수.
- 스케일:
  - `title` 20px / 700 — 화면 헤더
  - `body` 15px / 400 / line-height 1.55 — 말풍선 본문
  - `body-ko` 15px / 500 — KO 원문 (EN보다 살짝 굵게, 학습 대상 강조)
  - `caption` 12px / 500 — 라벨 배지, 타임스탬프, 문서명
  - `micro` 11px / 600 / letter-spacing 0.04em / uppercase — "원문", "ENGLISH" 언어 라벨

### 2.4 간격·형태

- 기본 간격 단위 4px. 화면 좌우 패딩 16px.
- 말풍선 radius: 16px, 발화자 쪽 하단 모서리만 4px (tail 느낌).
- 카드 radius: 12px. 버튼 radius: 12px. 배지 radius: 999px(pill).
- 그림자: 카드 `0 1px 3px rgba(45,55,72,0.08)`. 바텀시트 `0 -8px 24px rgba(45,55,72,0.12)`.

---

## 3. 화면 구성 (Screen: `ChatbotPage`)

```
┌─────────────────────────────┐
│ ① ChatHeader                │  sticky top
├─────────────────────────────┤
│                             │
│ ② MessageList (scroll)      │
│   ├ DateDivider             │
│   ├ BotWelcomeCard          │
│   ├ SuggestedQuestionChips  │
│   ├ UserBubble              │
│   ├ BotAnswerCard           │
│   │   ├ BilingualBlock      │
│   │   └ ReferenceStrip      │
│   ├ TypingIndicator         │
│   └ ErrorBubble             │
│                             │
├─────────────────────────────┤
│ ③ ChatInputBar              │  sticky bottom, safe-area
└─────────────────────────────┘
④ ReferenceSheet (bottom sheet, overlay)
```

---

## 4. 컴포넌트 인벤토리

### 4.1 ChatHeader

챗봇 화면 상단 고정 헤더.

- **구성**: 뒤로가기(chevron-left, lucide) · 봇 아바타(32px 원형, AI 아이콘) · 타이틀 2줄
  ("Ask K-Bridge" / 서브 "School & life documents") · 우측 `LanguageToggle`.
- **스타일**: 배경 `--color-card`, 하단 1px `--color-border`, 높이 56px.
- **상태**: 기본 / 스크롤 시(그림자 `0 1px 3px rgba(45,55,72,0.08)` 추가).

### 4.2 LanguageToggle

시스템 언어(EN/KO) 전환 세그먼트 컨트롤. **답변 병기 자체는 항상 유지**되고,
이 토글은 UI 라벨·안내 문구 언어만 바꾼다.

- **구성**: pill 컨테이너(배경 `#EDF2F7`) 안에 "EN" / "KO" 2개 세그먼트.
- **상태**: 활성 세그먼트 — 배경 `--color-primary`, 텍스트 흰색. 비활성 — 텍스트 `--color-muted`.
- **크기**: 높이 28px, 세그먼트 min-width 36px, `caption` 타이포.

### 4.3 UserBubble

- **정렬**: 우측. 최대 폭 78%.
- **스타일**: 배경 `--chat-user-bubble`, 텍스트 흰색, radius 16px/우하단 4px.
- **부속**: 말풍선 아래 우측 정렬 타임스탬프(`caption`, `--color-muted`).
- **상태**: 기본 / 전송 중(투명도 0.6 + 우측에 12px 스피너) / 실패(하단에 빨간
  "Failed to send · Tap to retry" 텍스트 버튼, `#E53E3E`).

### 4.4 BotAnswerCard

봇 답변의 컨테이너. 좌측 정렬, 최대 폭 88%. 배경 `--chat-bot-bubble`, 테두리
1px `--color-border`, radius 16px/좌하단 4px, 내부 패딩 14px.

내부는 위→아래 순서로:

1. **BilingualBlock** (§4.5) — 답변 본문 KO/EN 병기
2. 구분선 (`--color-border`, margin 10px 0) — 근거가 있을 때만
3. **ReferenceStrip** (§4.6) — 근거 문서 요약 줄

### 4.5 BilingualBlock  ★핵심 컴포넌트

KO 원문과 EN 번역을 병기하는 블록. 모바일 폭에서는 **세로 스택**(2열 아님).

```
┃ 원문                        ← micro 라벨 + KO 악센트 바
┃ 긴급 요청은 담당팀에 즉시
┃ 전달해야 합니다.
                               ← 8px 간격
┃ ENGLISH                     ← micro 라벨 + EN 악센트 바
┃ Urgent requests must be
┃ forwarded to the team
┃ immediately.
```

- **KO 섹션**: 좌측 3px 세로 바 `--chat-ko-accent`, 좌패딩 10px,
  라벨 "원문"(micro, `--chat-ko-accent`), 본문 `body-ko`.
- **EN 섹션**: 좌측 3px 세로 바 `--chat-en-accent`, 라벨 "ENGLISH"(micro,
  `#38A169` — success보다 한 단계 진하게, 대비 확보), 본문 `body`.
- **변형**:
  - `full` — 두 섹션 모두 표시 (기본).
  - `ko-only` — EN 번역 없음. EN 자리에 안내문
    "(English translation unavailable)" `caption`/`--color-muted`.
  - `en-only` — 원문이 영어 문서인 경우 EN 섹션만, 라벨 "ENGLISH" 유지.
- **긴 본문**: 6줄 초과 시 접기. "Show more / 더 보기" 텍스트 버튼(`caption`,
  `--color-primary`) — KO/EN 섹션이 함께 펼쳐진다(개별 접기 없음).

### 4.6 ReferenceStrip

BotAnswerCard 하단의 근거 문서 요약 줄. 탭하면 ReferenceSheet 오픈.

- **구성**: book-open 아이콘(14px, `--color-muted`) + "Sources · 3 documents"
  (`caption`, `--color-muted`) + 우측 chevron-right.
- **상태**: 기본 / pressed(배경 `#EDF2F7`).
- 근거 0건이면 스트립 자체를 렌더하지 않는다.

### 4.7 ReferenceSheet (Bottom Sheet)

근거 문서(RAG 검색 결과) 상세를 보여주는 바텀시트. 화면 높이 최대 80%.

- **헤더**: 그랩 핸들(36×4px pill, `--color-border`) + 타이틀 "Sources"(title 18px)
  + 우측 닫기(X) 아이콘 버튼.
- **본문**: `ReferenceCard` 목록 세로 스택, 간격 12px, 스크롤.
- **딤**: `rgba(45,55,72,0.4)`. 딤 탭/아래로 스와이프로 닫힘.

### 4.8 ReferenceCard

근거 문서 1건 카드.

- **컨테이너**: 배경 `--chat-ref-bg`, 테두리 1px `--color-border`, radius 12px, 패딩 12px.
- **1행**: 순위 배지(원형 20px, `--color-primary` 배경, 흰색 숫자) ·
  문서명 `caption`/600 (예: "visa_extension_guide.txt") · 우측 `ScoreBadge`.
- **2행**: 메타 `caption`/`--color-muted` — "chunk 2 · Korean (ko)".
- **3행**: **BilingualBlock** 재사용(`full` 변형, 4줄 클램프 + "더 보기").
- **상태**: 기본 / 펼침(클램프 해제).

### 4.9 ScoreBadge

유사도 점수 pill 배지.

- **구성**: 높이 20px pill, `micro` 타이포, 흰색 텍스트(low는 흰색 유지).
- **변형**: `high`(≥0.80, 배경 `--chat-score-high`, 라벨 "0.87") /
  `mid`(0.60–0.79, 배경 `--chat-score-mid`, 텍스트는 `--color-text`) /
  `low`(<0.60, 배경 `--chat-score-low`).

### 4.10 SuggestedQuestionChips

첫 진입 시 웰컴 카드 아래 추천 질문 칩. 가로 스크롤 1줄.

- **칩**: 배경 `--color-card`, 테두리 1px `--color-border`, radius 999px,
  패딩 8px 14px, `caption`/`--color-text`.
- 예시 문구: "How do I extend my visa?" · "기숙사 규칙 알려줘" · "Class schedule?"
- **상태**: 기본 / pressed(테두리·텍스트 `--color-primary`). 탭 시 해당 문구로 즉시 질문 전송.

### 4.11 BotWelcomeCard

대화가 비어 있을 때의 첫 봇 메시지.

- BotAnswerCard와 동일 컨테이너. 내용: 인사 1줄(EN) + 보조 1줄(KO) +
  "Answers come from registered school documents." `caption`/`--color-muted`.
- ReferenceStrip 없음.

### 4.12 TypingIndicator

- 좌측 정렬 소형 말풍선(BotAnswerCard 스타일, 패딩 12px 16px).
- 점 3개(6px 원, `--color-muted`) 순차 바운스 애니메이션 1.2s 루프.
- 검색 단계 표시(선택): 점 위에 `caption` "Searching documents…" → "Translating…".

### 4.13 ErrorBubble

봇 응답 실패 시.

- BotAnswerCard 컨테이너에 좌측 테두리 3px `#E53E3E`.
- 텍스트: "Something went wrong. / 답변을 가져오지 못했어요." `body`.
- 하단 "Retry" 텍스트 버튼(`caption`/600, `--color-primary`).

### 4.14 NoResultCard

검색 결과 0건일 때의 봇 답변 변형.

- BotAnswerCard 컨테이너. search-x 아이콘(20px, `--color-muted`) +
  "No matching document found. / 관련 문서를 찾지 못했어요." +
  보조 문구 "Try rephrasing, or ask a teacher." `caption`/`--color-muted`.
- ReferenceStrip 없음.

### 4.15 ChatInputBar

하단 고정 입력 바. safe-area-inset-bottom 반영.

- **컨테이너**: 배경 `--color-card`, 상단 1px `--color-border`, 패딩 8px 16px.
- **입력 필드**: 배경 `#EDF2F7`, radius 999px, 높이 44px(멀티라인 시 최대 3줄 확장),
  placeholder "Ask about school life…"(EN 모드) / "학교 생활에 대해 물어보세요"(KO 모드).
- **전송 버튼**: 44px 원형. 활성 — 배경 `--color-primary` + 흰색 send 아이콘(lucide).
  비활성(입력 없음) — 배경 `#EDF2F7` + `--color-muted` 아이콘.
- **상태**: 기본 / 입력 중 / 전송 중(버튼에 스피너, 입력 잠금) / 비활성.

### 4.16 DateDivider

- 중앙 정렬 pill: 배경 `#EDF2F7`, `caption`/`--color-muted`, 패딩 4px 12px.
- 라벨 예: "Today", "Yesterday", "Jun 30".

---

## 5. 인터랙션 플로우

1. **질문 전송**: 입력 → 전송 탭 → UserBubble 즉시 추가(전송 중 상태) →
   TypingIndicator 표시 → 응답 도착 시 BotAnswerCard로 교체. 자동 스크롤 최하단.
2. **근거 열람**: ReferenceStrip 탭 → ReferenceSheet 슬라이드 업(240ms ease-out) →
   카드별 "더 보기"로 청크 전문 확인.
3. **추천 질문**: 칩 탭 → 즉시 UserBubble로 전송. 첫 응답 후 칩 영역 제거.
4. **재시도**: 실패한 UserBubble 또는 ErrorBubble의 Retry 탭 → 동일 질문 재전송.
5. **언어 토글**: EN↔KO 전환 시 placeholder·라벨·안내 문구만 전환.
   기존 말풍선 내용은 리렌더하지 않는다.

## 6. 모션

- 새 말풍선 등장: opacity 0→1 + translateY 8px→0, 180ms ease-out.
- ReferenceSheet: translateY 100%→0, 240ms cubic-bezier(0.16, 1, 0.3, 1).
- TypingIndicator 점: scale 0.7→1, 스태거 150ms.
- 접기/펼치기: max-height 트랜지션 200ms. `prefers-reduced-motion` 시 모두 즉시 전환.

## 7. 접근성

- 색 대비: KO/EN 악센트 바는 장식 요소 — 라벨 텍스트("원문"/"ENGLISH")가 항상 동반되어
  색맹 사용자도 구분 가능해야 한다.
- ScoreBadge `mid`(노랑 배경)는 반드시 `--color-text` 텍스트 (흰색 금지, 대비 부족).
- 터치 타깃 최소 44×44px (전송 버튼, 칩, ReferenceStrip, 토글).
- 말풍선에 `role="log"` / `aria-live="polite"` 영역으로 신규 메시지 알림.
- `lang` 속성: KO 섹션 `lang="ko"`, EN 섹션 `lang="en"` — 스크린리더 발음 전환.

## 8. 카피 가이드

- 확답·보장 표현 금지(입학/비자/취업/장학 보장 워딩 불가). 근거 문서 기반임을 항상 명시.
- 봇 답변 하단 고정 디스클레이머(첫 답변에만 노출):
  "Based on registered documents. Please confirm important matters with staff."
- 에러·빈 결과 문구는 비난 없이 대안 제시("Try rephrasing…").

## 9. design-sync 카드 구성 제안

| Group | 카드 | 변형 포함 |
|---|---|---|
| Foundations | Colors & chatbot tokens | 기존 8토큰 + 확장 8토큰 |
| Foundations | Typography | title/body/body-ko/caption/micro |
| Chat | UserBubble | default / sending / failed |
| Chat | BotAnswerCard | with refs / no refs / welcome |
| Chat | BilingualBlock | full / ko-only / en-only / collapsed |
| Chat | TypingIndicator · ErrorBubble · NoResultCard | — |
| References | ReferenceStrip · ReferenceCard · ScoreBadge | score high/mid/low |
| References | ReferenceSheet | 전체 시트 레이아웃 |
| Input | ChatInputBar | idle / typing / sending / disabled |
| Navigation | ChatHeader · LanguageToggle · DateDivider · SuggestedQuestionChips | EN/KO |

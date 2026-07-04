# K-Bridge 문서 챗봇 (Ask K-Bridge) — UI 디자인 스펙 v2 (Bezier 기반)

> 대상: `KBridgeProject` 학생용 모바일 앱(React + Vite, 순수 CSS)의 신규 화면.
> 롤플레잉 게임과 별개인 **문서 기반 RAG 챗봇** — 학생이 생활/학사/비자 등 등록된 문서에 대해
> 질문하면, 문서 검색 결과를 근거로 답변하고 **한국어 원문 / English 번역을 병기**해서 보여준다.
> 이 문서는 Claude Design(design-sync)용 컴포넌트 사양서다.
>
> **v2 변경**: 디자인 시스템을 Channel Talk의 오픈소스 DS **Bezier**(MIT,
> `github.com/channel-io/bezier-react`) 기반으로 전면 교체. 레퍼런스:
> `docs/design/DESIGN-channeltalk-reference.md`. 챗봇은 메신저 제품이고 Bezier는
> 메신저를 위해 만들어진 시스템이라 궁합이 정확하다.

---

## 0. 결정 로그

| 날짜 | 결정 | 근거 |
|---|---|---|
| 2026-07-04 | v1: AGENTS.md 크림 팔레트(#FAF7F0/#336B8E) 기반 초안 | 기존 앱 화면과 통일 |
| 2026-07-04 | v2: Bezier(Channel Talk) 시스템으로 교체 | 사용자 결정. 챗봇 화면은 Bezier 규율을 따르며 **앱의 다른 화면(대시보드/게임)과 비주얼이 분리됨** — 추후 앱 전체 마이그레이션 여부는 별도 결정 필요 |

## 1. 제품 컨텍스트

- 사용자: 필리핀 까비떼 다스마리냐스 예일 국제 문화원의 10대 후반~20대 초반 학습자.
- 앱 기본 언어는 **영어(EN)**, 시스템 언어는 EN/KO 토글 가능.
- 챗봇의 답변 본문과 RAG 근거 문서는 **KO 원문 + EN 번역 병기**가 핵심 요구사항.
- 모바일처럼 보이는 React SPA, 최대 콘텐츠 폭 ~430px 프레임.

## 2. 디자인 토큰 (Bezier 기반)

### 2.1 색상

핵심 규율: **브랜드 액센트는 Cobalt 하나뿐**. 시맨틱 색(green/yellow/red)은
상태 표시 전용이며 장식에 쓰지 않는다. 본문은 순흑(#000)이 아닌 반투명 오프블랙.

| Token | 값 | 사용 위치 |
|---|---|---|
| `--chat-canvas` | `#FFFFFF` | 전체 배경 |
| `--chat-surface` | `#F7F7F8` (Grey 100) | 봇 말풍선, 스켈레톤, 입력 필드 |
| `--chat-surface-elevated` | `#FCFCFC` (Grey 50) | 시트/카드 표면 |
| `--chat-hairline` | `#EFEFF0` (Grey 200) | 구분선 |
| `--chat-border-alpha` | `rgba(0,0,0,0.05)` (Black 5) | 카드/입력 테두리 |
| `--chat-text` | `rgba(0,0,0,0.85)` (Black 85) | 본문 — **#000 금지** |
| `--chat-text-secondary` | `rgba(0,0,0,0.6)` (Black 60) | 보조 텍스트 |
| `--chat-muted` | `#A7A7AA` (Grey 500) | 타임스탬프, 메타 |
| `--chat-accent` | `#329BE7` (Cobalt 400) | 유일한 브랜드 액센트: 사용자 말풍선, 전송 버튼, KO 라벨, 활성 상태 |
| `--chat-accent-hover` | `#327AB8` (Cobalt 500) | pressed/hover |
| `--chat-accent-20` | `#329BE733` | ghost fill, 아바타 링 |
| `--chat-accent-10` | `#329BE71A` | subtle 배경 틴트 |
| `--chat-success` | `#31A552` (Green 400) | ScoreBadge high — 상태 전용 |
| `--chat-caution` | `#EDBC40` (Yellow 400) | ScoreBadge mid — 상태 전용 |
| `--chat-error` | `#E94E58` (Red 400) | 에러 배너 — 상태 전용 |
| `--chat-scrim` | `rgba(0,0,0,0.3)` (Black 30) | 바텀시트 딤 |

시맨틱 색 사용법: 솔리드 대신 **alpha-20 fill + 400색 텍스트** (예: 성공 배지 =
배경 `#31A55233` + 텍스트 `#31A552`). Bezier의 플랫 뎁스 시그니처.

### 2.2 타이포그래피

폰트: `Inter, "Noto Sans KR", NotoSansKR, -apple-system, "Segoe UI", Roboto, sans-serif`.
Inter가 기본이고 Noto Sans KR은 한글 글리프만 채운다 (한국어 우선 스택으로 바꾸지 말 것).

**웨이트는 400과 700만 사용한다** (Bezier 제품 크롬 규율 — 500/600 금지).

| 역할 | 스펙 | 사용 위치 |
|---|---|---|
| `title` | 22px / 700 / lh 28px / -0.4px | 시트 헤더 |
| `heading` | 16px / 700 / lh 24px / -0.1px | 화면 헤더 타이틀 |
| `body` | 15px / 400 / lh 20px / -0.1px | 말풍선 본문 (KO/EN 동일 — v1의 body-ko 500 웨이트는 폐기) |
| `caption` | 13px / 400 / lh 18px | 문서명, 메타, 타임스탬프 |
| `micro` | 11px / 700 / lh 16px / uppercase / ls 0.02em | "원문"/"ENGLISH" 라벨, 배지 |

KO 원문 강조는 웨이트가 아니라 **색**으로: KO 라벨과 악센트 바가 Cobalt, EN은 뉴트럴.

### 2.3 간격·형태·뎁스

- 간격: 4 / 8 / 12 / 16 / 20 / 24 / 32px 스케일. 화면 좌우 패딩 16px.
- **Radius 래더** (보간 금지 — 래더의 단만 사용): 4 / 8 / 12 / 16 / 20 / 9999.
  - 말풍선 16px (발화자 쪽 하단 모서리 4px)
  - 카드·입력 필드 8px, 근거 카드 12px, 바텀시트 상단 20px
  - 칩·배지·토글 9999(full)
- **뎁스는 플랫**: box-shadow 대신 표면 틴트(Grey 50/100) + Black 5 테두리.
  예외는 바텀시트(Level 4)만 — full shadow + Black 30 스크림.

### 2.4 모션

- 이징: `cubic-bezier(0.3, 0, 0, 1)` **하나만** 사용 (sharp-out / soft-in).
- 시간: s 150ms (hover/tint) · m 300ms (시트, 팝오버) · l 450ms (화면 전환).
- `prefers-reduced-motion`: duration → 0, transform → opacity 전용.

---

## 3. 화면 구성 (Screen: `ChatbotPage`)

```
┌─────────────────────────────┐
│ ① ChatHeader                │  sticky top, 흰 캔버스 + hairline
├─────────────────────────────┤
│ ② MessageList (scroll)      │  캔버스 #FFFFFF
│   ├ DateDivider             │
│   ├ BotWelcomeCard          │
│   ├ SuggestedQuestionChips  │
│   ├ UserBubble              │
│   ├ BotAnswerCard           │
│   │   ├ BilingualBlock      │
│   │   └ ReferenceStrip      │
│   ├ TypingIndicator         │
│   └ ErrorBanner             │
├─────────────────────────────┤
│ ③ ChatInputBar              │  sticky bottom, safe-area
└─────────────────────────────┘
④ ReferenceSheet (bottom sheet, Level 4 overlay)
```

---

## 4. 컴포넌트 인벤토리

### 4.1 ChatHeader

- **구성**: 뒤로가기(chevron-left) · 봇 아바타(32px 원형, `--chat-accent-20` 링 +
  Cobalt "AI") · 타이틀 2줄("Ask K-Bridge" heading / "School & life documents"
  caption muted) · 우측 `LanguageToggle`.
- **스타일**: 배경 `#FFFFFF`, 하단 1px `--chat-hairline`, 높이 56px. 그림자 없음
  (스크롤 시에도 — 플랫 규율).

### 4.2 LanguageToggle

UI 라벨 언어만 전환(EN/KO). 병기 표시는 항상 유지.

- **구성**: pill(9999) 컨테이너 배경 `--chat-surface`, 세그먼트 2개.
- **상태**: 활성 — 배경 `--chat-accent`, 흰 텍스트 700. 비활성 — `--chat-text-secondary` 400.
- 전환 트랜지션 150ms.

### 4.3 UserBubble

- **정렬**: 우측, 최대 폭 78%.
- **스타일**: 배경 `--chat-accent`, 흰 텍스트, radius 16px/우하단 4px. 테두리·그림자 없음.
- **상태**: 기본 / 전송 중(opacity 0.6 + 12px 스피너) / 실패(하단
  "Message not sent. Retry" — `--chat-error` 텍스트, Bezier 에러 카피 규칙:
  구체적 상황 + 액션 병기).

### 4.4 BotAnswerCard

- 좌측 정렬, 최대 폭 88%. 배경 `--chat-surface`(Grey 100), **테두리·그림자 없음**
  (표면 틴트가 뎁스), radius 16px/좌하단 4px, 패딩 14px.
- 내부: **BilingualBlock** → hairline 구분선(근거 있을 때만) → **ReferenceStrip**.

### 4.5 BilingualBlock  ★핵심 컴포넌트

KO 원문/EN 번역 병기. 모바일 폭에서 세로 스택.

- **KO 섹션**: 좌측 3px 바 `--chat-accent`(Cobalt), 라벨 "원문"(micro, Cobalt),
  본문 body. KO가 학습 대상 콘텐츠 = 브랜드 액센트 부여.
- **EN 섹션**: 좌측 3px 바 `--chat-muted`(뉴트럴), 라벨 "ENGLISH"(micro,
  `--chat-text-secondary`), 본문 body.
  - v1에서 EN에 그린 액센트를 썼으나 **폐기** — Bezier 규율상 시맨틱 색은 상태
    전용이며 장식 금지. 언어 구분은 Cobalt vs 뉴트럴로 충분하다.
- **변형**: `full` / `ko-only`(EN 자리에 "(English translation unavailable)"
  caption muted) / `en-only`.
- **긴 본문**: 6줄 초과 시 접기, "Show more · 더 보기" 텍스트 버튼(caption 700,
  Cobalt). KO/EN 함께 펼침.

### 4.6 ReferenceStrip

- book-open 아이콘(14px muted) + "Sources · 3 documents"(caption,
  `--chat-text-secondary`) + chevron-right.
- pressed: 배경 `--chat-accent-10` (cobalt ghost), 150ms.
- 근거 0건이면 미렌더.

### 4.7 ReferenceSheet (Bottom Sheet)

- Level 4: 배경 `--chat-canvas`, 상단 radius 20px, full shadow +
  `--chat-scrim` 딤. 진입 300ms `cubic-bezier(0.3,0,0,1)`.
- 헤더: 그랩 핸들(36×4px, hairline 색) + "Sources"(title) + 닫기 버튼(32px 원형,
  배경 `--chat-surface`).
- 본문: ReferenceCard 세로 스택 12px 간격, 최대 높이 80vh 스크롤.

### 4.8 ReferenceCard

- 배경 `--chat-surface-elevated`(Grey 50), 테두리 1px `--chat-border-alpha`,
  radius 12px, 패딩 12px. 그림자 없음.
- 1행: 순위 배지(20px 원형, `--chat-accent-20` 배경 + Cobalt 700 숫자 — 솔리드
  대신 ghost fill) · 문서명(caption 700) · ScoreBadge.
- 2행: 메타 caption muted — "chunk 2 · Korean (ko)".
- 3행: BilingualBlock(`full`, 2줄 클램프 + 더 보기).

### 4.9 ScoreBadge

상태 시맨틱이므로 시맨틱 색 사용 가능. alpha-20 fill + 400색 텍스트, pill(9999),
높이 20px, micro 타이포.

- `high`(≥0.80): 배경 `#31A55233`, 텍스트 `#31A552`
- `mid`(0.60–0.79): 배경 `#EDBC4033`, 텍스트 `#B08A20`(가독 보정 다크 옐로)
- `low`(<0.60): 배경 `rgba(0,0,0,0.05)`, 텍스트 `--chat-text-secondary`

### 4.10 SuggestedQuestionChips

- 칩: 배경 `#FFFFFF`, 테두리 1px `--chat-border-alpha`, radius 9999,
  패딩 8px 14px, caption `--chat-text`.
- pressed: 배경 `--chat-accent-10`, 테두리·텍스트 Cobalt.
- 예시: "How do I extend my visa?" · "기숙사 규칙 알려줘" · "Class schedule?"

### 4.11 BotWelcomeCard

- BotAnswerCard 컨테이너. 인사 1줄(EN) + 보조 1줄(KO) + 디스클레이머 caption muted:
  "Answers come from registered school documents."

### 4.12 TypingIndicator

- 소형 봇 말풍선(Grey 100). ALF 패턴 준용: 좌측에 20px 봇 아바타 + Cobalt accent 링
  (`--chat-accent-20` 2px).
- 점 3개(6px, muted) 바운스, 스태거 150ms.
- 단계 라벨(caption muted): "Searching documents…" → "Translating…".
- 스켈레톤 로딩(대화 이력): Grey 100 블록, **shimmer 없음** — 정적 틴트만.

### 4.13 ErrorBanner

Bezier §14 sync-failure 패턴: 말풍선이 아니라 **배너**.

- 배경 `#E94E5833`(red-400-20 fill), radius 8px, 패딩 10px 14px.
- 텍스트: "Message not sent. / 답변을 가져오지 못했어요."(caption, `--chat-text`)
  + 우측 "Retry" 텍스트 링크(caption 700, `--chat-error`).

### 4.14 NoResultCard

- BotAnswerCard 컨테이너(Grey 100). search-x 아이콘(20px muted) +
  "No matching document found. / 관련 문서를 찾지 못했어요." +
  "Try rephrasing, or ask a teacher." caption muted.

### 4.15 ChatInputBar

- 컨테이너: 배경 `#FFFFFF`, 상단 1px hairline, 패딩 8px 16px, safe-area 반영.
- 입력 필드: Bezier input 스펙 — 배경 `#FFFFFF`, 테두리 1px `--chat-border-alpha`,
  **radius 8px**(pill 아님 — 래더 준수), 높이 44px(멀티라인 최대 3줄),
  패딩 8px 12px. 포커스: `#329BE74D`(cobalt-400-30) 아웃라인 링.
  placeholder(muted): "Ask about school life…" / "학교 생활에 대해 물어보세요".
- 전송 버튼: 44px 원형(9999). 활성 — 배경 `--chat-accent` + 흰 send 아이콘,
  pressed `--chat-accent-hover`. 비활성 — 배경 `--chat-surface` + muted 아이콘.
- 전송 중: 버튼에 스피너, 입력 잠금(opacity 0.4 — Bezier disabled 규칙).

### 4.16 DateDivider

- 중앙 pill: 배경 `--chat-surface`, caption muted, 패딩 4px 12px.

---

## 5. 인터랙션 플로우

1. **질문 전송**: 입력 → 전송 → UserBubble 즉시 추가(전송 중) → TypingIndicator →
   응답 도착 시 BotAnswerCard. 자동 스크롤 최하단.
2. **근거 열람**: ReferenceStrip 탭 → ReferenceSheet 300ms 슬라이드 업 →
   카드별 더 보기.
3. **추천 질문**: 칩 탭 → 즉시 전송. 첫 응답 후 칩 제거.
4. **재시도**: 실패 UserBubble 또는 ErrorBanner의 Retry → 동일 질문 재전송.
5. **언어 토글**: placeholder·라벨만 전환, 기존 말풍선 유지.

## 6. 접근성

- KO/EN 악센트 바는 장식 — 텍스트 라벨("원문"/"ENGLISH")이 항상 동반.
- 시맨틱 배지의 alpha fill + 컬러 텍스트 조합은 대비 4.5:1 이상 확인
  (mid 옐로는 텍스트를 `#B08A20`으로 어둡게 보정).
- 터치 타깃 최소 44×44px.
- 메시지 영역 `role="log"` / `aria-live="polite"`.
- KO 섹션 `lang="ko"`, EN 섹션 `lang="en"`.

## 7. 카피 가이드

- 확답·보장 표현 금지(입학/비자/취업/장학 보장 워딩 불가).
- 에러는 구체적 상황 + 액션 병기: "Message not sent. Retry" (Bezier 에러 카피 규칙).
- 첫 답변에 디스클레이머: "Based on registered documents. Please confirm important
  matters with staff."
- Channel Talk 마케팅 카피 차용 금지(IP 가드레일) — 톤 셰이프만 참고.

## 8. design-sync 카드 구성

| Group | 카드 | 변형 |
|---|---|---|
| Foundations | Colors (Bezier 챗봇 토큰) | 캔버스/텍스트/Cobalt 래더/시맨틱 |
| Foundations | Typography | title/heading/body/caption/micro, 400·700만 |
| Chat | UserBubble | default / sending / failed |
| Chat | BotAnswerCard | with refs / welcome |
| Chat | BilingualBlock | full / ko-only / en-only / collapsed |
| Chat | Status | typing(ALF 링) / error banner / no result |
| References | ReferenceCard · ScoreBadge | high/mid/low alpha-fill |
| References | ReferenceSheet | Level 4 시트 |
| Input | ChatInputBar | idle / typing / sending / KO |
| Navigation | ChatHeader · LanguageToggle · DateDivider · Chips | EN/KO |

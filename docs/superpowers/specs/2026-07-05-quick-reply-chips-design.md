# Quick-reply chip menu for the chatbot (sub-project 1 of 4)

## Context

This is the first of four independent backend/product sub-projects identified
while porting the Claude Design "K-Bridge AI" onboarding-chatbot prototype
(`유학원 챗봇.dc.html`) into `KBridgeProject/frontend`. The other three
(K-Pass content vetting, a real visit-booking system, live agent handoff) are
out of scope here and will get their own spec/plan cycles.

Investigation confirmed the four topics the design's quick-reply menu covers
— ARC, SIM/phone, bank account, hospital/health-insurance — already exist as
real, working scenarios in the live backend (`C:\KBridge\k_bridge_admin`,
port 8050) and are correctly routed by the existing classifier from free-text
input (verified live: "ARC 신청 어떻게 하나요?" → `K1_GUIDE` /
`arc_registration`). No backend change is required for this sub-project.

## Goal

Add a quick-reply chip menu to the chatbot UI (`ChatbotMainPage.jsx`) so
students can tap a topic instead of typing, matching the design's UX pattern.
Chips send their canned query text through the existing `sendChatMessage`
pipeline — identical to typing the same text.

## Non-goals

- No backend/classifier changes.
- No per-turn "smart" chip suggestions based on backend response content.
- No exclusion of the just-discussed topic and no separate "back to menu"
  chip — see Simplification below.

## Design

### Data

A static, frontend-only constant:

```js
const QUICK_MENU = [
  { key: 'arc', label: 'ARC 안내', query: '외국인등록증 신청 방법 알려주세요' },
  { key: 'sim', label: '유심/휴대폰', query: '휴대폰 유심 개통은 어떻게 하나요' },
  { key: 'bank', label: '은행계좌', query: '은행 계좌는 어떻게 개설하나요' },
  { key: 'hospital', label: '병원/보험', query: '병원 진료나 건강보험은 어떻게 하나요' },
];
```

Query strings are chosen to match keyword patterns already proven to route
correctly against the live classifier (verified for ARC; SIM/bank/hospital
use the same phrasing style as their known scenario ids `sim_card`,
`bank_account`, `hospital_first_visit`).

### Message flow

- The initial greeting is followed by one `{ kind: 'chips', chips: QUICK_MENU }`
  entry in local `messages` state (rendered, not sent to the backend).
- After every assistant turn completes (whether triggered by a typed message
  or a chip click), append the same full `QUICK_MENU` chips entry again.
- Clicking a chip: sets the input value to the chip's `query` is not needed —
  it calls the same submit path `handleSubmit` uses today, passing the
  chip's `query` text directly, so it behaves exactly like the student typed
  and sent that text (same busy/error/student-guard behavior, no new code
  path in `sendChatMessage`).

### Simplification (agreed during brainstorming)

Original design prototype excluded the just-discussed topic from the
follow-up chip set and added a distinct "back to menu" chip. This requires
mapping arbitrary free-text turns back to a topic key, which is unreliable.
Simplified: **always show the same full 4-chip menu after every turn** — no
exclusion logic, no separate "back to menu" chip (redundant since the full
menu is already always present).

### Components

- New presentational component `QuickReplyChips({ chips, onSelect, disabled })`
  — renders a wrapping row of pill buttons, reusing the visual language
  already shipped in the earlier chatbot redesign (accent-blue soft
  background, rounded pill, same font scale as existing chip-like elements).
- `ChatMessage` gains a branch for `message.kind === 'chips'` alongside the
  existing student/bot branches.
- `handleSubmit` currently reads the text to send from the `input` state
  closure. It will accept an optional `overrideText` argument; when passed
  (chip click), it sends that text without touching the `input` state. When
  omitted (form submit), behavior is unchanged. `QuickReplyChips`'s
  `onSelect` calls `handleSubmit(chip.query)`.

### Error handling

No new error states. Chip buttons are disabled under the same conditions the
send button already uses today (`busy`, `loadingStudents`, no
`selectedStudentId`) — reusing existing `disabled` props, not new logic.

### Testing

Manual verification against the live dev server (`localhost:5174`) and live
backend (port 8050, per `frontend/.env`): click each of the 4 chips once and
confirm the response card type/scenario matches the intended topic (ARC →
`K1_GUIDE`/`arc_registration`, etc., following the same verification already
done for ARC and the safety path). No new automated test suite exists for
this component tree today, so no automated tests are added — this can be
revisited if/when the frontend gains a test harness.

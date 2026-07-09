# Quick-Reply Chip Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a quick-reply chip menu (ARC / SIM / bank / hospital) to the K-Bridge chatbot UI so students can tap a topic instead of typing, reusing the existing chat pipeline unchanged.

**Architecture:** Frontend-only change to `frontend/src/views/ChatbotMainPage.jsx` and `frontend/src/styles/chatbot.css`. A static `QUICK_MENU` constant drives a new `QuickReplyChips` presentational component. Clicking a chip calls the same submit path a typed message uses, sending the chip's canned query text through the existing, unmodified `sendChatMessage` → live backend (port 8050) → classifier pipeline.

**Tech Stack:** React 18 (function components, hooks), plain CSS (no CSS-in-JS/framework), Vite dev server (already running on `localhost:5174`), no test framework installed in this project.

## Global Constraints

- No backend changes of any kind (spec: "No backend/classifier changes").
- Exactly these 4 chips, in this order, with this exact query text (spec §Data):
  - `{ key: 'arc', label: 'ARC 안내', query: '외국인등록증 신청 방법 알려주세요' }`
  - `{ key: 'sim', label: '유심/휴대폰', query: '휴대폰 유심 개통은 어떻게 하나요' }`
  - `{ key: 'bank', label: '은행계좌', query: '은행 계좌는 어떻게 개설하나요' }`
  - `{ key: 'hospital', label: '병원/보험', query: '병원 진료나 건강보험은 어떻게 하나요' }`
- The chip menu shown after every assistant turn is always the full, unfiltered 4-chip list — no "exclude the topic just discussed" logic, no separate "back to menu" chip (spec §Simplification).
- Chip buttons must be disabled under exactly the same conditions the existing send button uses today: `busy || loadingStudents || !selectedStudentId` (spec §Error handling).
- No new automated test suite — this project has no test framework installed (`frontend/package.json` has no test script/devDependencies) and the spec explicitly scopes verification to manual browser checks against the live dev server + live backend.
- Visual style must reuse the existing accent-blue design tokens already defined in `chatbot.css` (`--kb-accent-blue`, `--kb-accent-blue-soft`) — no new colors introduced.

---

### Task 1: Refactor `handleSubmit` to accept an optional override text

**Files:**
- Modify: `frontend/src/views/ChatbotMainPage.jsx:490-534` (the `handleSubmit` function inside `ChatbotMainPage`)

**Interfaces:**
- Consumes: nothing new — same component state (`input`, `busy`, `selectedStudentId`, `loadingStudents`, `conversationId`) already in scope.
- Produces: `handleSubmit(overrideText?: string)` — when called with no argument (or a non-string), behaves exactly as today (reads from the `input` state). When called with a string argument, sends that string instead, ignoring the current `input` state value for the text to send. Task 2's `QuickReplyChips` will call `handleSubmit(chip.query)`.

- [ ] **Step 1: Confirm current manual behavior as a baseline**

The dev server is already running at `http://localhost:5174` (per `.tmp_frontend.log`; if not running, start it with `npm run dev` from `frontend/`). Open it in a browser, wait for a student to load in the dropdown, type any message (e.g. `테스트`) into the input box, and press send. Confirm: the message appears as a student bubble, then an assistant response appears, input box clears, and no errors show in the browser console. This is the behavior Step 3 must not change.

- [ ] **Step 2: Edit `handleSubmit`'s signature and text source**

In `frontend/src/views/ChatbotMainPage.jsx`, change:

```js
  async function handleSubmit() {
    const text = input.trim();
```

to:

```js
  async function handleSubmit(overrideText) {
    const text = (typeof overrideText === 'string' ? overrideText : input).trim();
```

Leave every other line inside `handleSubmit` unchanged (the validation, `setError`, `setInput('')`, `setBusy(true)`, the `sendChatMessage` call, and the `try`/`catch`/`finally` block all stay exactly as they are — `setInput('')` still unconditionally clears the input box, which is fine whether the call came from typing or from a chip).

- [ ] **Step 3: Re-run the manual check from Step 1**

Reload `http://localhost:5174`, repeat the exact same manual check from Step 1 (type a message, send it, confirm student bubble → assistant response → cleared input, no console errors). This confirms the refactor is behavior-preserving for the typed-message path before Task 2 adds the second caller.

- [ ] **Step 4: Commit**

```bash
cd C:/KBridge/KBridgeProject
git add frontend/src/views/ChatbotMainPage.jsx
git commit -m "refactor(chatbot): handleSubmit accepts optional override text

Prepares handleSubmit to be called with a fixed string (for the
upcoming quick-reply chips) as well as from the typed-input form,
with no change to the typed-input behavior."
```

---

### Task 2: Add the quick-reply chip menu (component, styles, state wiring)

**Files:**
- Modify: `frontend/src/views/ChatbotMainPage.jsx` (add `QUICK_MENU` constant, add `QuickReplyChips` component, extend `ChatMessage`, wire chips into initial/reset/post-response message state, pass new props at the render call site)
- Modify: `frontend/src/styles/chatbot.css` (add `.chat-message.is-menu`, `.chat-quick-menu`, `.chat-quick-chip`, `.chat-quick-chip:disabled`)

**Interfaces:**
- Consumes: `handleSubmit(overrideText?: string)` from Task 1.
- Produces: a `{ id, kind: 'chips', chips: QUICK_MENU }` message shape recognized by `ChatMessage`. No other task depends on anything from this task.

- [ ] **Step 1: Add the `QUICK_MENU` constant**

In `frontend/src/views/ChatbotMainPage.jsx`, immediately after the closing `};` of `SAFETY_QUICK_ACTIONS_BY_SUBTYPE` (currently ending at line 79) and before `function makeId(prefix) {` (currently line 81), insert:

```js

const QUICK_MENU = [
  { key: 'arc', label: 'ARC 안내', query: '외국인등록증 신청 방법 알려주세요' },
  { key: 'sim', label: '유심/휴대폰', query: '휴대폰 유심 개통은 어떻게 하나요' },
  { key: 'bank', label: '은행계좌', query: '은행 계좌는 어떻게 개설하나요' },
  { key: 'hospital', label: '병원/보험', query: '병원 진료나 건강보험은 어떻게 하나요' },
];
```

- [ ] **Step 2: Add the `QuickReplyChips` component**

Immediately after the `ChatInput` function (which currently ends at line 419, right before `export default function ChatbotMainPage`), insert a new component:

```js
function QuickReplyChips({ chips, onSelect, disabled }) {
  return (
    <div className="chat-quick-menu" role="group" aria-label="Quick reply options">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          className="chat-quick-chip"
          disabled={disabled}
          onClick={() => onSelect(chip.query)}
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Extend `ChatMessage` to render chip messages**

`ChatMessage` currently starts like this (lines 359-369):

```js
function ChatMessage({ message }) {
  const isStudent = message.role === 'student';

  if (isStudent) {
```

Change it to accept two new props and branch on `message.kind === 'chips'` first:

```js
function ChatMessage({ message, onSelectChip, chipsDisabled }) {
  if (message.kind === 'chips') {
    return (
      <div className="chat-message is-menu">
        <QuickReplyChips chips={message.chips} onSelect={onSelectChip} disabled={chipsDisabled} />
      </div>
    );
  }

  const isStudent = message.role === 'student';

  if (isStudent) {
```

Leave the rest of `ChatMessage` (the student branch and the bot branch) exactly as-is.

- [ ] **Step 4: Show the chip menu after the initial greeting**

Change the `messages` state initializer (currently line 425):

```js
  const [messages, setMessages] = useState([DEFAULT_GREETING]);
```

to:

```js
  const [messages, setMessages] = useState([
    DEFAULT_GREETING,
    { id: 'chips-initial', kind: 'chips', chips: QUICK_MENU },
  ]);
```

- [ ] **Step 5: Show the chip menu again after reset and after a student switch**

`handleReset` (currently lines 469-475) and `handleStudentChange` (currently lines 477-488) each call `setMessages([DEFAULT_GREETING]);`. Change both occurrences to:

```js
    setMessages([DEFAULT_GREETING, { id: makeId('chips'), kind: 'chips', chips: QUICK_MENU }]);
```

(There are exactly two occurrences of `setMessages([DEFAULT_GREETING]);` in the file — one in each function. Replace both.)

- [ ] **Step 6: Show the chip menu again after every assistant response**

Inside `handleSubmit`'s `try` block (currently lines 512-528), the assistant message is appended like this:

```js
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: makeId('assistant'),
          role: 'assistant',
          response,
          time: formatChatTime(),
        },
      ]);
      setLastDebugData(response);
```

Change the `setMessages` call to also append a fresh chips entry in the same update:

```js
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: makeId('assistant'),
          role: 'assistant',
          response,
          time: formatChatTime(),
        },
        { id: makeId('chips'), kind: 'chips', chips: QUICK_MENU },
      ]);
      setLastDebugData(response);
```

Do not add a chips entry in the `catch` block — only on a successful response, so a chip menu never appears directly under an error message.

- [ ] **Step 7: Pass the new props at the render call site**

The message list is rendered like this (currently lines 555-557):

```js
          {messages.map((message) => (
            <ChatMessage message={message} key={message.id} />
          ))}
```

Change it to:

```js
          {messages.map((message) => (
            <ChatMessage
              message={message}
              onSelectChip={handleSubmit}
              chipsDisabled={busy || loadingStudents || !selectedStudentId}
              key={message.id}
            />
          ))}
```

- [ ] **Step 8: Add the chip styles to `chatbot.css`**

Append to the end of `frontend/src/styles/chatbot.css`:

```css

.chat-message.is-menu {
  margin: 2px 0 17px 42px;
}

.chat-quick-menu {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chat-quick-chip {
  padding: 8px 14px;
  border: 1px solid rgba(97, 87, 234, 0.3);
  border-radius: 999px;
  background: var(--kb-accent-blue-soft);
  color: var(--kb-accent-blue);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.chat-quick-chip:disabled {
  opacity: 0.45;
  cursor: default;
}
```

- [ ] **Step 9: Manual verification against the live dev server and live backend**

Reload `http://localhost:5174` (Vite HMR should pick up the changes automatically; hard-reload if anything looks stale). With a student selected:

1. Confirm the 4 chips (`ARC 안내`, `유심/휴대폰`, `은행계좌`, `병원/보험`) appear right after the greeting bubble, styled as blue-accent pill buttons under the avatar column.
2. Click `ARC 안내`. Confirm: a student bubble reading "외국인등록증 신청 방법 알려주세요" appears, followed by an assistant `K1_GUIDE` card about Alien Registration (matches the response already verified for this query earlier in this project), followed by the same 4-chip menu again.
3. Click `유심/휴대폰`, then `은행계좌`, then `병원/보험` in turn. For each, confirm a relevant assistant response card appears (the classifier is expected to route these to the `sim_card`, `bank_account`, and `hospital_first_visit` scenarios respectively — if any of the three does not return a topically relevant card, note the exact response received and stop here rather than adjusting classifier-facing query text, since Global Constraints fixes the exact query strings; report it back instead of improvising a fix), and that the chip menu reappears each time.
4. Type a free-text message instead of clicking a chip; confirm it still sends normally and is followed by a chip menu.
5. Click the reset button (header, circular refresh icon) and confirm the conversation resets to greeting + chip menu.
6. Open the browser console and confirm no new errors appeared during any of the above.

- [ ] **Step 10: Commit**

```bash
cd C:/KBridge/KBridgeProject
git add frontend/src/views/ChatbotMainPage.jsx frontend/src/styles/chatbot.css
git commit -m "feat(chatbot): add quick-reply chip menu (ARC/SIM/bank/hospital)

Frontend-only: chips send their canned query through the existing
handleSubmit/sendChatMessage path, so the already-live classifier
routes them exactly like typed text. No backend changes."
```

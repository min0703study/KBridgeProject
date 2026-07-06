import { useEffect, useRef, useState } from 'react';
import {
  Battery,
  Briefcase,
  CheckCircle2,
  ChevronRight,
  HeartPulse,
  Info,
  MessageSquare,
  Mic,
  Phone,
  RefreshCw,
  Send,
  ShieldCheck,
  Signal,
  Siren,
  Wifi,
} from 'lucide-react';
import { getChatStudents, sendChatMessage } from '../api/chatApi.js';
import AppBottomNavigation from '../components/AppBottomNavigation.jsx';
import ChatDebugPanel from '../components/ChatDebugPanel.jsx';

// chat_dev.html(k_bridge_admin) 이관 디버그 패널 — ?debug=1 로 열었을 때만 노출.
const DEBUG_ENABLED =
  typeof window !== 'undefined' && new URLSearchParams(window.location.search).has('debug');

const DEFAULT_GREETING = {
  id: 'bot-greeting',
  role: 'assistant',
  time: '9:41 AM',
  text: ['안녕하세요! 👋', "I’m K-Bridge AI.", 'How can I help you with', 'your Korean today?'],
};

const DEFAULT_SAFETY_HOTLINES = [
  { label: '경찰 (범죄·신변 위협)', tel: '112' },
  { label: '응급의료·구조', tel: '119' },
  { label: '24시간 통역 도움', tel: '1330' },
];

const SAFETY_QUICK_ACTIONS_BY_SUBTYPE = {
  emotional_crisis: [
    { label: '자살예방상담', tel: '1393', icon: 'heart' },
    { label: '응급', tel: '119', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '다누리(위기)', tel: '1366', icon: 'heart' },
    { label: '학교 담당자', tel: '02-1234-5678', icon: 'briefcase' },
    { label: '운영자', tel: '010-9876-5432', icon: 'heart' },
  ],
  external_threat: [
    { label: '경찰', tel: '112', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '출입국·체류', tel: '1345', icon: 'briefcase' },
    { label: '다누리(폭력)', tel: '1366', icon: 'siren' },
    { label: '운영자', tel: '010-9876-5432', icon: 'heart' },
  ],
  labor_exploitation: [
    { label: '노동상담', tel: '1350', icon: 'briefcase' },
    { label: '경찰', tel: '112', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '다누리(착취)', tel: '1366', icon: 'briefcase' },
    { label: '운영자', tel: '010-9876-5432', icon: 'heart' },
  ],
  medical_emergency: [
    { label: '응급', tel: '119', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '경찰', tel: '112', icon: 'siren' },
  ],
  fraud: [
    { label: '경찰', tel: '112', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '노동상담', tel: '1350', icon: 'briefcase' },
  ],
  default_l3: [
    { label: '경찰', tel: '112', icon: 'siren' },
    { label: '응급', tel: '119', icon: 'siren' },
    { label: '통역', tel: '1330', icon: 'heart' },
    { label: '다누리', tel: '1366', icon: 'heart' },
    { label: '학교 담당자', tel: '02-1234-5678', icon: 'briefcase' },
    { label: '운영자', tel: '010-9876-5432', icon: 'heart' },
  ],
};

const QUICK_MENU = [
  { key: 'arc', label: 'ARC 안내', en: 'Alien Registration', query: '외국인등록증 신청 방법 알려주세요' },
  { key: 'sim', label: '유심/휴대폰', en: 'Phone & SIM', query: '휴대폰 유심 개통은 어떻게 하나요' },
  { key: 'bank', label: '은행계좌', en: 'Bank account', query: '은행 계좌는 어떻게 개설하나요' },
  { key: 'hospital', label: '병원/보험', en: 'Hospital & insurance', query: '병원 진료나 건강보험은 어떻게 하나요' },
  { key: 'message', label: '운영자에게 메시지', en: 'Leave a message', action: 'message' },
];

const DEFAULT_COUNSELOR = '김서연 매니저';
const DEFAULT_REPLY_WINDOW = '영업일 기준 1일 이내 · 카카오톡 또는 전화';

function makeId(prefix) {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatChatTime(date = new Date()) {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  });
}

function normalizeLines(text) {
  if (Array.isArray(text)) {
    return text;
  }
  return String(text || '').split('\n');
}

function ChatbotStatusBar() {
  return (
    <div className="phone-status-bar" aria-label="Mock phone status bar">
      <span className="phone-time">9:41</span>
      <div className="phone-island" aria-hidden="true">
        <span />
      </div>
      <div className="phone-indicators" aria-hidden="true">
        <Signal size={18} strokeWidth={3} />
        <Wifi size={18} strokeWidth={3} />
        <Battery size={22} strokeWidth={2.5} />
      </div>
    </div>
  );
}

function ChatbotHeader({
  profileInitial,
  students,
  selectedStudentId,
  selectedStudent,
  onStudentChange,
  onReset,
  loadingStudents,
}) {
  return (
    <header className="dashboard-header chatbot-header">
      <img
        className="yici-logo"
        src="/01_yici_logo_lockup.png"
        alt="KBridge Project"
      />
      <div className="header-actions">
        <div className="language-toggle" aria-label="Mock language toggle">
          <button className="language-option is-active" type="button">
            EN
          </button>
          <button className="language-option" type="button">
            KR
          </button>
        </div>
        <button className="profile-button" type="button" aria-label="Mock profile">
          {profileInitial}
        </button>
      </div>
      <div className="chatbot-identity-row">
        <div className="chatbot-avatar">
          <img src="/ai_icon.png" alt="" aria-hidden="true" />
          <span className="chatbot-avatar-status" aria-hidden="true" />
        </div>
        <div className="chatbot-identity-text">
          <div className="chatbot-identity-title">
            <span>K-Bridge</span>
            <span className="chatbot-ai-badge">AI</span>
          </div>
          <div className="chatbot-identity-sub">학생 지원 도우미 · Student support assistant</div>
        </div>
      </div>
      <div className="chatbot-session-row">
        <label className="chatbot-student-select-label" htmlFor="chatbot-student-select">
          Student
        </label>
        <select
          id="chatbot-student-select"
          className="chatbot-student-select"
          value={selectedStudentId}
          disabled={loadingStudents || students.length === 0}
          onChange={(event) => onStudentChange(event.target.value)}
          aria-label="Select student profile"
        >
          {loadingStudents ? (
            <option value="">Loading student...</option>
          ) : students.length ? (
            students.map((student) => (
              <option value={student.id} key={student.id}>
                {student.name} - {student.visa_type || 'Student'}
              </option>
            ))
          ) : (
            <option value="">Student unavailable</option>
          )}
        </select>
        <span>
          {loadingStudents
            ? 'Loading student...'
            : selectedStudent
              ? `${selectedStudent.name} · ${selectedStudent.visa_type || 'Student'}`
              : 'Student unavailable'}
        </span>
        <button className="chatbot-reset-button" type="button" onClick={onReset} aria-label="Reset chat">
          <RefreshCw size={14} strokeWidth={2.2} />
        </button>
      </div>
    </header>
  );
}

function SourceBadges({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className="chat-card-sources">
      {sources.map((source, index) => (
        <span className="chat-card-source" key={`${source?.title || 'source'}-${index}`}>
          {source && typeof source === 'object' && 'title' in source
            ? source.title
            : `출처 ${index + 1}`}
        </span>
      ))}
    </div>
  );
}

function GenericChatCard({ card }) {
  if (!card) {
    return null;
  }

  const renderUnknownList = (items) => (
    <ul className="chat-card-list">
      {items.map((item, index) => (
        <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
      ))}
    </ul>
  );

  return (
    <section className={`chat-response-card tone-${String(card.type || 'default').toLowerCase()}`}>
      <div className="chat-card-header">
        <span className="chat-card-icon" aria-hidden="true">
          <Info size={16} strokeWidth={2.3} />
        </span>
        <div className="chat-card-title">
          <span>[{card.type}]</span>
          {card.title}
        </div>
      </div>
      {card.answer ? <p className="chat-card-answer">{card.answer}</p> : null}
      {card.steps?.length ? (
        <ol className="chat-card-steps">
          {card.steps.map((step, index) => (
            <li key={`${step}-${index}`}>
              <span className="chat-card-step-number">{index + 1}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      ) : null}
      {card.interpretations?.length ? renderUnknownList(card.interpretations) : null}
      {card.today_cards?.length ? renderUnknownList(card.today_cards) : null}
      {card.hotlines?.length ? (
        <div className="private-hotline-list">
          {card.hotlines.map((h) => (
            <a className="private-hotline-row" href={`tel:${h.tel}`} key={h.tel}>
              <Phone size={18} strokeWidth={2.1} aria-hidden="true" />
              <strong>{h.label}</strong>
              <span>{h.tel}</span>
            </a>
          ))}
        </div>
      ) : null}
      <SourceBadges sources={card.sources} />
    </section>
  );
}

function SafetyIcon({ icon }) {
  if (icon === 'siren') {
    return <Siren size={24} strokeWidth={2.1} aria-hidden="true" />;
  }
  if (icon === 'briefcase') {
    return <Briefcase size={24} strokeWidth={2.1} aria-hidden="true" />;
  }
  return <HeartPulse size={24} strokeWidth={2.1} aria-hidden="true" />;
}

function SafetyCard({ card }) {
  const hotlines = card.hotlines?.length ? card.hotlines : DEFAULT_SAFETY_HOTLINES;
  const quickActions =
    SAFETY_QUICK_ACTIONS_BY_SUBTYPE[card.red_subtype] ||
    SAFETY_QUICK_ACTIONS_BY_SUBTYPE.default_l3;

  return (
    <section className="safety-response" aria-label="Emergency support contacts">
      <div className="safety-main-card">
        <div className="safety-heading-row">
          <span className="safety-shield" aria-hidden="true">
            <ShieldCheck size={30} strokeWidth={1.9} />
          </span>
          <div>
            <h2>{card.title || '지금 바로 도움을 받을 수 있어요'}</h2>
            <p>당신의 안전과 마음의 안정을 위해, 언제든지 도움을 요청할 수 있어요.</p>
          </div>
        </div>

        <div className="safety-hotline-list">
          {hotlines.map((hotline, index) => (
            <a className="safety-hotline-row" href={`tel:${hotline.tel}`} key={`${hotline.label}-${hotline.tel}`}>
              <span className="safety-number">{index + 1}</span>
              <strong>{hotline.label}</strong>
              <b>{hotline.tel}</b>
              <Phone size={20} strokeWidth={2.1} aria-hidden="true" />
            </a>
          ))}
        </div>
      </div>

      <div className="safety-action-grid">
        {quickActions.map((action) => (
          <a className="safety-action-card" href={`tel:${action.tel}`} key={action.tel}>
            <span className="safety-action-icon">
              <SafetyIcon icon={action.icon} />
            </span>
            <span>{action.label}</span>
            <strong>{action.tel}</strong>
            <ChevronRight size={14} strokeWidth={2.4} className="safety-action-chevron" aria-hidden="true" />
          </a>
        ))}
      </div>

      <p className="safety-closing">당신의 삶은 소중해요. 꼭 도움을 받아보세요. 🌱</p>
    </section>
  );
}

function AssistantResponse({ response }) {
  const isSafety = response?.card?.type === 'K5_SAFETY';

  if (isSafety) {
    return (
      <>
        {response.bubble ? <BubbleText text={response.bubble} /> : null}
        <SafetyCard card={response.card} />
      </>
    );
  }

  return (
    <>
      <GenericChatCard card={response?.card} />
      {response?.bubble ? <BubbleText text={response.bubble} /> : null}
    </>
  );
}

function BubbleText({ text }) {
  return (
    <div className="chat-bubble">
      {normalizeLines(text).map((line, index) => (
        <span key={`${line}-${index}`}>{line}</span>
      ))}
    </div>
  );
}

function ComposeCard({ message, onInputChange, onSubmit, disabled }) {
  if (message.sent) {
    return (
      <section className="chat-compose-card is-sent">
        <div className="chat-compose-header">
          <span className="chat-compose-icon" aria-hidden="true">
            <MessageSquare size={18} strokeWidth={2.2} />
          </span>
          <div>
            <div className="chat-compose-title">Message sent</div>
            <div className="chat-compose-subtitle">메시지가 전달됐어요</div>
          </div>
        </div>
        <p className="chat-compose-sent-text">{message.sentText}</p>
      </section>
    );
  }

  return (
    <section className="chat-compose-card">
      <div className="chat-compose-header">
        <span className="chat-compose-icon" aria-hidden="true">
          <MessageSquare size={18} strokeWidth={2.2} />
        </span>
        <div>
          <div className="chat-compose-title">Leave a message for your manager</div>
          <div className="chat-compose-subtitle">운영자에게 메시지 남기기 · 영업일 기준 1일 이내 답변</div>
        </div>
      </div>
      <textarea
        className="chat-compose-textarea"
        placeholder="도움이 필요한 내용을 적어주세요 · Type what you need help with..."
        value={message.text}
        disabled={disabled}
        onChange={(event) => onInputChange(message.id, event.target.value)}
      />
      <button
        type="button"
        className="chat-compose-submit"
        disabled={disabled || !message.text.trim()}
        onClick={() => onSubmit(message.id)}
      >
        전송 · Send to manager
      </button>
    </section>
  );
}

function ConfirmCard({ message }) {
  return (
    <section className="chat-confirm-card">
      <div className="chat-confirm-header">
        <span className="chat-confirm-icon" aria-hidden="true">
          <CheckCircle2 size={20} strokeWidth={2.2} />
        </span>
        <div>
          <div className="chat-confirm-title">Message sent</div>
          <div className="chat-confirm-subtitle">메시지가 전달됐어요</div>
        </div>
      </div>
      <div className="chat-confirm-row">
        <span>담당 매니저 · To</span>
        <strong>{message.counselor}</strong>
      </div>
      <div className="chat-confirm-row">
        <span>답변 예정 · Reply by</span>
        <strong>{message.replyBy}</strong>
      </div>
    </section>
  );
}

function ChatMessage({ message, onSelectChip, chipsDisabled, onComposeInput, onComposeSubmit }) {
  if (message.kind === 'chips') {
    return (
      <div className="chat-message is-menu">
        <QuickReplyChips chips={message.chips} onSelect={onSelectChip} disabled={chipsDisabled} />
      </div>
    );
  }

  if (message.kind === 'compose') {
    return (
      <div className="chat-message is-menu">
        <ComposeCard
          message={message}
          onInputChange={onComposeInput}
          onSubmit={onComposeSubmit}
          disabled={chipsDisabled || message.sent}
        />
      </div>
    );
  }

  if (message.kind === 'confirm') {
    return (
      <div className="chat-message is-menu">
        <ConfirmCard message={message} />
      </div>
    );
  }

  const isStudent = message.role === 'student';

  if (isStudent) {
    return (
      <article className="chat-message is-student">
        <BubbleText text={message.text} />
        <time>{message.time}</time>
      </article>
    );
  }

  return (
    <article className="chat-message is-bot">
      <div className="chat-bot-avatar" aria-hidden="true">
        <img src="/ai_icon.png" alt="" />
      </div>
      <div className="chat-bot-content">
        {message.response ? (
          <AssistantResponse response={message.response} />
        ) : (
          <BubbleText text={message.text} />
        )}
        <time>{message.time}</time>
      </div>
    </article>
  );
}

function ChatInput({ value, busy, disabled, onChange, onSubmit }) {
  return (
    <form
      className="chat-input-bar"
      aria-label="KBridge chatbot message form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <input
        type="text"
        placeholder={disabled ? 'Student profile is loading...' : 'Type a message...'}
        aria-label="Type a message"
        value={value}
        disabled={busy || disabled}
        onChange={(event) => onChange(event.target.value)}
      />
      <button className="chat-icon-button" type="button" aria-label="Record voice message">
        <Mic size={27} strokeWidth={2.1} />
      </button>
      <button
        className="chat-send-button"
        type="submit"
        aria-label="Send message"
        disabled={busy || disabled || !value.trim()}
      >
        <Send size={25} strokeWidth={2.4} />
      </button>
    </form>
  );
}

function QuickReplyChips({ chips, onSelect, disabled }) {
  return (
    <div className="chat-quick-menu" role="group" aria-label="Quick reply options">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          className="chat-quick-chip"
          disabled={disabled}
          onClick={() => onSelect(chip)}
        >
          <span className="chat-quick-chip-ko">{chip.label}</span>
          {chip.en ? <span className="chat-quick-chip-en">{chip.en}</span> : null}
        </button>
      ))}
    </div>
  );
}

export default function ChatbotMainPage({ activeTab, onMockNavigate }) {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [conversationId, setConversationId] = useState(() => makeId('conversation'));
  const [messages, setMessages] = useState([
    DEFAULT_GREETING,
    { id: 'chips-initial', kind: 'chips', chips: QUICK_MENU },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [error, setError] = useState('');
  const [lastDebugData, setLastDebugData] = useState(null);
  const [showDebug, setShowDebug] = useState(false);
  const conversationRef = useRef(null);

  const selectedStudent = students.find((student) => student.id === selectedStudentId) || null;

  useEffect(() => {
    let cancelled = false;

    getChatStudents()
      .then((list) => {
        if (cancelled) return;
        const safeList = Array.isArray(list) ? list : [];
        setStudents(safeList);
        setSelectedStudentId(safeList[0]?.id || '');
        setError(safeList.length ? '' : 'No demo students were returned by the chat server.');
      })
      .catch((requestError) => {
        if (cancelled) return;
        setError(requestError instanceof Error ? requestError.message : 'Failed to load students.');
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingStudents(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    conversationRef.current?.scrollTo({
      top: conversationRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, busy, error]);

  function handleReset() {
    setConversationId(makeId('conversation'));
    setMessages([DEFAULT_GREETING, { id: makeId('chips'), kind: 'chips', chips: QUICK_MENU }]);
    setInput('');
    setError('');
    setLastDebugData(null);
  }

  function handleStudentChange(studentId) {
    if (studentId === selectedStudentId) {
      return;
    }

    setSelectedStudentId(studentId);
    setConversationId(makeId('conversation'));
    setMessages([DEFAULT_GREETING, { id: makeId('chips'), kind: 'chips', chips: QUICK_MENU }]);
    setInput('');
    setError('');
    setLastDebugData(null);
  }

  function handleChipSelect(chip) {
    if (chip.action === 'message') {
      setMessages((currentMessages) => [
        ...currentMessages,
        { id: makeId('compose'), kind: 'compose', text: '', sent: false, sentText: '' },
      ]);
      return;
    }
    handleSubmit(chip.query);
  }

  function handleComposeInput(msgId, text) {
    setMessages((currentMessages) =>
      currentMessages.map((message) => (message.id === msgId ? { ...message, text } : message)),
    );
  }

  function handleComposeSubmit(msgId) {
    const target = messages.find((message) => message.id === msgId);
    const text = (target?.text || '').trim();
    if (!text || busy) {
      return;
    }

    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === msgId ? { ...message, sent: true, sentText: text } : message,
      ),
    );
    setBusy(true);

    window.setTimeout(() => {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: makeId('confirm'),
          kind: 'confirm',
          counselor: DEFAULT_COUNSELOR,
          replyBy: DEFAULT_REPLY_WINDOW,
        },
        {
          id: makeId('assistant'),
          role: 'assistant',
          text: '감사해요. 담당 매니저가 영업일 기준 1일 이내에 카카오톡 또는 전화로 연락드릴게요.',
          time: formatChatTime(),
        },
        { id: makeId('chips'), kind: 'chips', chips: QUICK_MENU },
      ]);
      setBusy(false);
    }, 700);
  }

  async function handleSubmit(overrideText) {
    const text = (typeof overrideText === 'string' ? overrideText : input).trim();
    if (!text || busy || !selectedStudentId) {
      if (!selectedStudentId && !loadingStudents) {
        setError('A student profile is required before sending chat messages.');
      }
      return;
    }

    setError('');
    setInput('');
    setBusy(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: makeId('student'),
        role: 'student',
        text,
        time: formatChatTime(),
      },
    ]);

    try {
      const response = await sendChatMessage({
        studentId: selectedStudentId,
        conversationId,
        text,
      });

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
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Failed to send message.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-stage">
      <div className="mobile-shell chatbot-shell">
        <ChatbotStatusBar />
        <ChatbotHeader
          profileInitial="H"
          students={students}
          selectedStudentId={selectedStudentId}
          selectedStudent={selectedStudent}
          loadingStudents={loadingStudents}
          onStudentChange={handleStudentChange}
          onReset={handleReset}
        />
        <section
          className="chatbot-conversation"
          aria-label="KBridge AI conversation"
          ref={conversationRef}
        >
          <div className="chat-spacer" aria-hidden="true" />
          {messages.map((message) => (
            <ChatMessage
              message={message}
              onSelectChip={handleChipSelect}
              chipsDisabled={busy || loadingStudents || !selectedStudentId}
              onComposeInput={handleComposeInput}
              onComposeSubmit={handleComposeSubmit}
              key={message.id}
            />
          ))}
          {busy ? (
            <article className="chat-message is-bot">
              <div className="chat-bot-avatar" aria-hidden="true">
                <img src="/ai_icon.png" alt="" />
              </div>
              <div
                className="chat-bubble chat-typing-dots"
                role="status"
                aria-label="응답을 준비하고 있어요"
              >
                <span aria-hidden="true" />
                <span aria-hidden="true" />
                <span aria-hidden="true" />
              </div>
            </article>
          ) : null}
          {error ? <div className="chatbot-error">{error}</div> : null}
        </section>
        <ChatInput
          value={input}
          busy={busy}
          disabled={loadingStudents || !selectedStudentId}
          onChange={setInput}
          onSubmit={handleSubmit}
        />
        <AppBottomNavigation activeTab={activeTab} onNavigate={onMockNavigate} />
        {DEBUG_ENABLED && !showDebug ? (
          <button
            className="chat-debug-toggle"
            type="button"
            onClick={() => setShowDebug(true)}
            aria-label="Open debug panel"
          >
            DEV
          </button>
        ) : null}
        {DEBUG_ENABLED && showDebug ? (
          <ChatDebugPanel data={lastDebugData} onClose={() => setShowDebug(false)} />
        ) : null}
      </div>
    </main>
  );
}

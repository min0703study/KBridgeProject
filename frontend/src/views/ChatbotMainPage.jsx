import { useEffect, useRef, useState } from 'react';
import {
  Battery,
  Briefcase,
  ChevronRight,
  HeartPulse,
  LayoutGrid,
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
import { MOCK_BOTTOM_NAV_ITEMS } from '../mock/mockDashboardData.js';

const DEFAULT_GREETING = {
  id: 'bot-greeting',
  role: 'assistant',
  time: '9:41 AM',
  text: ['안녕하세요! 👋', "I’m K-Bridge AI.", 'How can I help you with', 'your Korean today?'],
};

const DEFAULT_SAFETY_HOTLINES = [
  { label: '자살예방상담', tel: '1393' },
  { label: '외국인 도움', tel: '1345' },
  { label: '긴급', tel: '112' },
];

const SAFETY_QUICK_ACTIONS = [
  { label: '자살예방상담', tel: '1393', icon: 'heart' },
  { label: '긴급', tel: '112', icon: 'siren' },
  { label: '노동상담', tel: '1350', icon: 'briefcase' },
];

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
      <div className="chat-card-title">
        <span>[{card.type}]</span>
        {card.title}
      </div>
      {card.answer ? <p className="chat-card-answer">{card.answer}</p> : null}
      {card.steps?.length ? (
        <ol className="chat-card-steps">
          {card.steps.map((step, index) => (
            <li key={`${step}-${index}`}>{step}</li>
          ))}
        </ol>
      ) : null}
      {card.interpretations?.length ? renderUnknownList(card.interpretations) : null}
      {card.today_cards?.length ? renderUnknownList(card.today_cards) : null}
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
        {SAFETY_QUICK_ACTIONS.map((action) => (
          <a className="safety-action-card" href={`tel:${action.tel}`} key={action.tel}>
            <span className="safety-action-icon">
              <SafetyIcon icon={action.icon} />
            </span>
            <span>{action.label}</span>
            <strong>{action.tel}</strong>
            <ChevronRight size={22} strokeWidth={2.2} aria-hidden="true" />
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

function ChatMessage({ message }) {
  const isStudent = message.role === 'student';

  return (
    <article className={`chat-message is-${isStudent ? 'student' : 'bot'}`}>
      {isStudent || !message.response ? (
        <BubbleText text={message.text} />
      ) : (
        <AssistantResponse response={message.response} />
      )}
      <time>{message.time}</time>
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

function ChatbotBottomNavigation({ onMockNavigate }) {
  return (
    <nav className="bottom-nav" aria-label="Mock app navigation">
      {MOCK_BOTTOM_NAV_ITEMS.map((item) => (
        <button
          className={`nav-item ${item.tab === 'chatbot' ? 'is-active' : ''}`}
          type="button"
          key={item.id}
          onClick={() => {
            if (
              item.tab === 'dashboard' ||
              item.tab === 'homework' ||
              item.tab === 'chatbot'
            ) {
              onMockNavigate(item.tab);
            }
          }}
        >
          {item.iconSrc ? (
            <img src={item.iconSrc} alt={item.iconAlt} />
          ) : (
            <LayoutGrid size={30} strokeWidth={1.9} aria-hidden="true" />
          )}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

export default function ChatbotMainPage({ onMockNavigate }) {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('');
  const [conversationId, setConversationId] = useState(() => makeId('conversation'));
  const [messages, setMessages] = useState([DEFAULT_GREETING]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [error, setError] = useState('');
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
    setMessages([DEFAULT_GREETING]);
    setInput('');
    setError('');
  }

  function handleStudentChange(studentId) {
    if (studentId === selectedStudentId) {
      return;
    }

    setSelectedStudentId(studentId);
    setConversationId(makeId('conversation'));
    setMessages([DEFAULT_GREETING]);
    setInput('');
    setError('');
  }

  async function handleSubmit() {
    const text = input.trim();
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
      ]);
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
            <ChatMessage message={message} key={message.id} />
          ))}
          {busy ? (
            <article className="chat-message is-bot">
              <div className="chat-bubble chat-bubble-status">
                <span>응답을 준비하고 있어요...</span>
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
        <ChatbotBottomNavigation onMockNavigate={onMockNavigate} />
      </div>
    </main>
  );
}

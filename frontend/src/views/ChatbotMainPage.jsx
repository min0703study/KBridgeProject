import {
  Battery,
  Gamepad2,
  LayoutGrid,
  Mic,
  Send,
  Signal,
  Wifi,
} from 'lucide-react';
import { MOCK_BOTTOM_NAV_ITEMS } from '../mock/mockDashboardData.js';

const MOCK_MESSAGES = [
  {
    id: 'bot-greeting',
    from: 'bot',
    time: '9:41 AM',
    text: ['안녕하세요! 👋', "I’m K-Bridge AI.", 'How can I help you with', 'your Korean today?'],
  },
  {
    id: 'student-question',
    from: 'student',
    time: '9:42 AM',
    text: ['I need help with a sentence', 'I’m practicing.'],
  },
  {
    id: 'bot-follow-up',
    from: 'bot',
    time: '9:42 AM',
    text: ['Sure! Send it over and', "I’ll help you understand it", 'better. 😊'],
  },
];

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

function ChatbotHeader({ profileInitial }) {
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
    </header>
  );
}

function ChatMessage({ message }) {
  return (
    <article className={`chat-message is-${message.from}`}>
      <div className="chat-bubble">
        {message.text.map((line) => (
          <span key={line}>{line}</span>
        ))}
      </div>
      <time>{message.time}</time>
    </article>
  );
}

function ChatInput() {
  return (
    <form
      className="chat-input-bar"
      aria-label="Mock chatbot message form"
      onSubmit={(event) => event.preventDefault()}
    >
      <input type="text" placeholder="Type a message..." aria-label="Type a message" />
      <button className="chat-icon-button" type="button" aria-label="Record voice message">
        <Mic size={27} strokeWidth={2.1} />
      </button>
      <button className="chat-send-button" type="button" aria-label="Send message">
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
              item.tab === 'game' ||
              item.tab === 'homework' ||
              item.tab === 'chatbot'
            ) {
              onMockNavigate(item.tab);
            }
          }}
        >
          {item.iconSrc ? (
            <img src={item.iconSrc} alt={item.iconAlt} />
          ) : item.lucide === 'game' ? (
            <Gamepad2 size={30} strokeWidth={1.9} aria-hidden="true" />
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
  return (
    <main className="app-stage">
      <div className="mobile-shell chatbot-shell">
        <ChatbotStatusBar />
        <ChatbotHeader profileInitial="H" />
        <section className="chatbot-conversation" aria-label="KBridge AI mock conversation">
          <div className="chat-spacer" aria-hidden="true" />
          {MOCK_MESSAGES.map((message) => (
            <ChatMessage message={message} key={message.id} />
          ))}
        </section>
        <ChatInput />
        <ChatbotBottomNavigation onMockNavigate={onMockNavigate} />
      </div>
    </main>
  );
}

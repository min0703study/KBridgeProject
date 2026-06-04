import {
  ChevronLeft,
  Gamepad2,
  Menu,
  Mic,
  Send,
  Settings,
  Star,
  Volume2,
} from 'lucide-react';
import { getMockConvenienceStoreInGameData } from '../mock/mockGameData.js';

function MockRoleplayTopBar({ data, onMockBack }) {
  return (
    <header className="roleplay-top-bar">
      <button className="roleplay-circle-button" type="button" aria-label="Back to roleplay list" onClick={onMockBack}>
        <ChevronLeft size={28} strokeWidth={2.4} aria-hidden="true" />
      </button>
      <h1>{data.title}</h1>
      <span className={`roleplay-level-pill tone-${data.difficultyTone}`}>{data.difficulty}</span>
      <button className="roleplay-small-button" type="button" aria-label="Mock roleplay settings">
        <Settings size={20} strokeWidth={2.1} aria-hidden="true" />
      </button>
      <button className="roleplay-circle-button menu-button" type="button" aria-label="Mock roleplay menu">
        <Menu size={28} strokeWidth={2.5} aria-hidden="true" />
      </button>
    </header>
  );
}

function MockConversationBubble({ message }) {
  const isClerk = message.speaker === 'clerk';

  return (
    <div className={`conversation-row ${isClerk ? 'is-clerk' : 'is-student'}`}>
      <div className="conversation-bubble">
        {message.hasAudio ? (
          <button className="audio-button" type="button" aria-label="Mock play conversation audio">
            <Volume2 size={20} strokeWidth={2.3} aria-hidden="true" />
          </button>
        ) : null}
        <p>{message.text}</p>
      </div>
    </div>
  );
}

function MockResponseBar({ placeholder }) {
  return (
    <div className="roleplay-response-dock">
      <button className="favorite-response-button" type="button" aria-label="Mock favorite phrase">
        <Star size={32} strokeWidth={2.4} aria-hidden="true" />
      </button>
      <button className="response-input-button" type="button">
        <span>{placeholder}</span>
        <Mic size={28} strokeWidth={2.4} aria-hidden="true" />
      </button>
      <button className="send-response-button" type="button" aria-label="Mock send response">
        <Send size={30} strokeWidth={2.3} aria-hidden="true" />
      </button>
    </div>
  );
}

export default function RoleplayInGamePage({ onMockBack }) {
  const mockInGameData = getMockConvenienceStoreInGameData();

  return (
    <main className="app-stage">
      <div className="mobile-shell roleplay-shell">
        <img
          className="roleplay-bg"
          src={mockInGameData.backgroundImageSrc}
          alt={mockInGameData.backgroundImageAlt}
        />
        <div className="roleplay-bg-shade" aria-hidden="true" />
        <div className="roleplay-notch" aria-hidden="true">
          <span />
        </div>
        <MockRoleplayTopBar data={mockInGameData} onMockBack={onMockBack} />
        <section className="conversation-stack" aria-label="Mock roleplay conversation">
          {mockInGameData.messages.map((message) => (
            <MockConversationBubble message={message} key={message.id} />
          ))}
        </section>
        <MockResponseBar placeholder={mockInGameData.responsePlaceholder} />
        <Gamepad2 className="roleplay-hidden-marker" size={1} aria-hidden="true" />
      </div>
    </main>
  );
}

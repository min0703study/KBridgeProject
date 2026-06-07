import { useEffect, useRef, useState } from 'react';
import {
  ArrowUp,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  Lightbulb,
  Menu,
  Mic,
  Settings,
  ShieldCheck,
  Sparkles,
  Speaker,
  Star,
  Volume2,
  X,
} from 'lucide-react';
import { sendConvenienceStoreTurn } from '../api/roleplayApi.js';
import { createWavRecorder } from '../utils/wavRecorder.js';

const INITIAL_USER_MESSAGE = {
  id: 'sample-user-message',
  tone: 'learner',
  ko: '죄송하지만, 신분증 확인 부탁드립니다.',
  en: "I'm sorry, may I check your ID?",
  hasFeedback: true,
};

const DEFAULT_FEEDBACK = {
  previous_text: '신분증 줘요',
  better_way: '죄송하지만, 신분증 확인 부탁드립니다.',
  politeness_note:
    'To sound more polite, avoid a direct command and add a softener with a respectful request.',
  grammar_note:
    'Use “신분증 확인” to say “ID check” instead of asking the listener to hand over the ID directly.',
};

function formatSeconds(seconds) {
  return `00:${String(seconds).padStart(2, '0')}`;
}

function Waveform() {
  return (
    <div className="roleplay-waveform" aria-hidden="true">
      {Array.from({ length: 34 }).map((_, index) => (
        <span style={{ '--bar-index': index }} key={index} />
      ))}
    </div>
  );
}

function DialogueBubble({ tone, ko, en, onFeedbackClick, active }) {
  return (
    <article className={`roleplay-dialogue-bubble ${tone}`}>
      <button className="dialogue-audio-button" type="button" aria-label="Play dialogue audio">
        <Volume2 size={22} strokeWidth={2.4} aria-hidden="true" />
      </button>
      <p lang="ko">{ko}</p>
      <span aria-hidden="true" />
      <p>{en}</p>
      <button className="dialogue-collapse-button" type="button" aria-label="Collapse dialogue">
        <ChevronDown size={20} strokeWidth={2.6} aria-hidden="true" />
      </button>
      {onFeedbackClick ? (
        <button
          className={`dialogue-feedback-button ${active ? 'is-active' : ''}`}
          type="button"
          aria-label="Toggle correction feedback"
          onClick={onFeedbackClick}
        >
          <Sparkles size={20} fill="currentColor" aria-hidden="true" />
        </button>
      ) : null}
    </article>
  );
}

function FeedbackPanel({ feedback, onClose }) {
  return (
    <section className="correction-panel" aria-label="Correction Feedback">
      <div className="correction-header">
        <Sparkles size={24} fill="currentColor" aria-hidden="true" />
        <h2>Correction Feedback</h2>
        <button type="button" aria-label="Close correction feedback" onClick={onClose}>
          <X size={22} aria-hidden="true" />
        </button>
      </div>

      <div className="correction-tabs" aria-label="Feedback categories">
        <span className="correction-tab is-politeness">
          <ShieldCheck size={22} aria-hidden="true" />
          politeness
        </span>
        <span className="correction-tab is-grammar">
          <BookOpen size={22} aria-hidden="true" />
          grammar
        </span>
      </div>

      <div className="correction-card">
        <div className="previous-row">
          <span>Previous</span>
          <p lang="ko">{feedback.previous_text}</p>
        </div>
        <div className="correction-divider" />
        <strong>Better way</strong>
        <h3 lang="ko">{feedback.better_way}</h3>
        <div className="correction-note is-politeness">
          <ShieldCheck size={24} aria-hidden="true" />
          <p>{feedback.politeness_note}</p>
        </div>
        <div className="correction-note is-grammar">
          <BookOpen size={24} aria-hidden="true" />
          <p>{feedback.grammar_note}</p>
        </div>
      </div>
    </section>
  );
}

export default function RoleplayIngamePage({ onBack }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [messages, setMessages] = useState([INITIAL_USER_MESSAGE]);
  const [feedback, setFeedback] = useState(DEFAULT_FEEDBACK);
  const [showFeedback, setShowFeedback] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      if (recorderRef.current) {
        recorderRef.current.cancel();
      }
    };
  }, []);

  async function startRecording() {
    setErrorMessage('');
    try {
      recorderRef.current = await createWavRecorder();
      setRecordingSeconds(0);
      setIsRecording(true);
      timerRef.current = setInterval(() => {
        setRecordingSeconds((value) => value + 1);
      }, 1000);
    } catch (error) {
      setErrorMessage(error.message || 'Microphone permission is required.');
    }
  }

  async function cancelRecording() {
    clearInterval(timerRef.current);
    timerRef.current = null;
    if (recorderRef.current) {
      await recorderRef.current.cancel();
      recorderRef.current = null;
    }
    setIsRecording(false);
    setRecordingSeconds(0);
  }

  async function sendRecording() {
    if (!recorderRef.current) {
      return;
    }

    clearInterval(timerRef.current);
    timerRef.current = null;
    setIsRecording(false);
    setIsSending(true);
    setErrorMessage('');

    try {
      const audioBlob = await recorderRef.current.stop();
      recorderRef.current = null;
      const payload = await sendConvenienceStoreTurn({
        audioBlob,
        clientTurnId: crypto.randomUUID(),
      });

      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          tone: 'learner',
          ko: payload.transcript,
          en: 'Voice response recorded.',
          hasFeedback: Boolean(payload.feedback),
        },
        {
          id: crypto.randomUUID(),
          tone: 'customer',
          ko: payload.assistant_message.ko,
          en: payload.assistant_message.en,
          hasFeedback: false,
        },
      ]);

      if (payload.feedback) {
        setFeedback(payload.feedback);
        setShowFeedback(Boolean(payload.ui_state?.should_show_feedback));
      }

      if (payload.assistant_message?.audio_base64) {
        const audio = new Audio(
          `data:${payload.assistant_message.audio_mime_type};base64,${payload.assistant_message.audio_base64}`,
        );
        audioRef.current = audio;
        audio.play().catch(() => {});
      }
    } catch (error) {
      setErrorMessage(error.message || 'Could not send this voice turn.');
    } finally {
      setIsSending(false);
      setRecordingSeconds(0);
    }
  }

  const latestFeedbackMessage = [...messages].reverse().find((message) => message.hasFeedback);

  return (
    <main className="app-stage roleplay-stage">
      <div className="mobile-shell roleplay-ingame-shell">
        <img
          className="roleplay-scene-bg"
          src="/roleplay_ingame_image/roleplay_convenience_store_customer.png"
          alt=""
          aria-hidden="true"
        />
        <div className="roleplay-scene-scrim" aria-hidden="true" />

        <header className="roleplay-topbar">
          <button type="button" aria-label="Back to roleplay list" onClick={onBack}>
            <ChevronLeft size={34} strokeWidth={2.5} aria-hidden="true" />
          </button>
          <h1>Convenience Store</h1>
          <span className="roleplay-difficulty">Easy</span>
          <button type="button" aria-label="Settings">
            <Settings size={31} strokeWidth={2.8} aria-hidden="true" />
          </button>
          <button type="button" aria-label="Menu">
            <Menu size={34} strokeWidth={2.5} aria-hidden="true" />
          </button>
        </header>

        <section className="roleplay-step-card" aria-label="Current step">
          <div className="step-title-row">
            <span className="step-number">01</span>
            <strong>Step 1: Check your ID.</strong>
          </div>
          <div className="step-progress-row">
            <span className="step-progress-track">
              <span />
            </span>
            <b>0 / 5</b>
            <div className="step-hearts" aria-label="5 chances remaining">
              {Array.from({ length: 5 }).map((_, index) => (
                <span key={index}>♥</span>
              ))}
            </div>
          </div>
        </section>

        <div className="roleplay-tip">
          <span>
            <Lightbulb size={22} strokeWidth={2.4} aria-hidden="true" />
          </span>
          You must check your ID for alcoholic beverages!
        </div>

        <section className="roleplay-content-stack" aria-label="Conversation">
          <article className="roleplay-info-card">
            <BookOpen size={30} fill="currentColor" strokeWidth={1.8} aria-hidden="true" />
            <p>Among the items the customer wants to purchase is beer, which requires age verification.</p>
          </article>

          <article className="roleplay-action-card">
            <Sparkles size={26} aria-hidden="true" />
            <p>The customer places a beer on the counter.</p>
          </article>

          <DialogueBubble tone="customer" ko="계산해 주세요." en="Please check out." />

          {messages.map((message) => (
            <DialogueBubble
              tone={message.tone}
              ko={message.ko}
              en={message.en}
              key={message.id}
              active={showFeedback && latestFeedbackMessage?.id === message.id}
              onFeedbackClick={
                message.hasFeedback
                  ? () => {
                      setShowFeedback((value) => !value);
                    }
                  : null
              }
            />
          ))}
        </section>

        {showFeedback ? <FeedbackPanel feedback={feedback} onClose={() => setShowFeedback(false)} /> : null}

        {errorMessage ? <p className="roleplay-error">{errorMessage}</p> : null}

        <footer className={`roleplay-composer ${isRecording ? 'is-recording' : ''}`}>
          {isRecording ? (
            <>
              <button className="composer-cancel" type="button" aria-label="Cancel recording" onClick={cancelRecording}>
                <X size={35} strokeWidth={2.5} aria-hidden="true" />
              </button>
              <Waveform />
              <time>{formatSeconds(recordingSeconds)}</time>
            </>
          ) : (
            <>
              <button className="composer-star" type="button" aria-label="Favorite phrase">
                <Star size={34} fill="currentColor" strokeWidth={2.5} aria-hidden="true" />
              </button>
              <div className="composer-input">
                <span>{isSending ? 'Sending voice...' : 'Type a message...'}</span>
                <button
                  type="button"
                  aria-label="Start voice recording"
                  onClick={startRecording}
                  disabled={isSending}
                >
                  <Mic size={30} strokeWidth={2.8} aria-hidden="true" />
                </button>
              </div>
            </>
          )}
          <button
            className="composer-send"
            type="button"
            aria-label={isRecording ? 'Send voice recording' : 'Send message'}
            onClick={isRecording ? sendRecording : undefined}
            disabled={isSending}
          >
            {isSending ? (
              <Speaker size={29} strokeWidth={2.4} aria-hidden="true" />
            ) : (
              <ArrowUp size={36} strokeWidth={2.6} aria-hidden="true" />
            )}
          </button>
        </footer>
      </div>
    </main>
  );
}

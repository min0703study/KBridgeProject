import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowUp,
  BookOpen,
  ChevronDown,
  ChevronLeft,
  Heart,
  Lightbulb,
  Menu,
  Mic,
  ShieldCheck,
  Sparkles,
  Speaker,
  Star,
  Volume2,
  X,
} from 'lucide-react';
import { getConvenienceStoreIngame, sendRoleplaySessionTurn } from '../api/roleplayApi.js';
import { createWavRecorder } from '../utils/wavRecorder.js';

const FALLBACK_BACKGROUND_IMAGE = '/roleplay_ingame_image/roleplay_convenience_store_customer.png';

function formatSeconds(seconds) {
  return `00:${String(seconds).padStart(2, '0')}`;
}

function getTranslationText(translationJson, preferredLanguage = 'en') {
  if (!translationJson || typeof translationJson !== 'object') {
    return '';
  }

  return (
    translationJson[preferredLanguage] ||
    translationJson[preferredLanguage?.toLowerCase?.()] ||
    translationJson.en ||
    translationJson.EN ||
    ''
  );
}

function formatStepNumber(stepOrder) {
  return String(stepOrder || 1).padStart(2, '0');
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

function mapTurnMessages(payload) {
  const turnMessages = Array.isArray(payload.turn_messages) ? payload.turn_messages : [];
  let feedbackAttached = false;

  return turnMessages
    .map((message) => {
      const id = message.message_id || crypto.randomUUID();
      const translatedText = getTranslationText(message.translation_json);

      if (message.message_type === 'learner_input_text') {
        const hasFeedback = Boolean(payload.feedback) && !feedbackAttached;
        feedbackAttached = feedbackAttached || hasFeedback;
        return {
          id,
          type: 'dialogue',
          tone: 'learner',
          ko: message.text_content,
          en: translatedText || 'Voice response recorded.',
          hasFeedback,
        };
      }

      if (message.message_type === 'roleplay_character_dialogue_text') {
        return {
          id,
          type: 'dialogue',
          tone: 'customer',
          ko: message.text_content,
          en: translatedText,
          hasFeedback: false,
        };
      }

      if (message.message_type === 'scene_text') {
        return {
          id,
          type: 'card',
          kind: 'scene',
          text: message.text_content,
        };
      }

      if (message.message_type === 'roleplay_character_action_text') {
        return {
          id,
          type: 'card',
          kind: 'action',
          text: message.text_content,
        };
      }

      if (message.message_type === 'hint') {
        return {
          id,
          type: 'card',
          kind: 'hint',
          text: message.text_content,
        };
      }

      return null;
    })
    .filter(Boolean);
}

function DialogueBubble({ tone, ko, en, onFeedbackClick, active }) {
  return (
    <article className={`roleplay-dialogue-bubble ${tone}`}>
      <button className="dialogue-audio-button" type="button" aria-label="Play dialogue audio">
        <Volume2 size={22} strokeWidth={2.4} aria-hidden="true" />
      </button>
      <p lang="ko">{ko}</p>
      {en ? (
        <>
          <span aria-hidden="true" />
          <p>{en}</p>
        </>
      ) : null}
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

function TurnMessageCard({ message }) {
  if (message.kind === 'scene') {
    return (
      <article className="roleplay-info-card">
        <BookOpen size={24} fill="currentColor" strokeWidth={1.8} aria-hidden="true" />
        <p>{message.text}</p>
      </article>
    );
  }

  if (message.kind === 'action') {
    return (
      <article className="roleplay-action-card">
        <Sparkles size={26} aria-hidden="true" />
        <p>{message.text}</p>
      </article>
    );
  }

  if (message.kind === 'hint') {
    return (
      <article className="roleplay-turn-hint">
        <Lightbulb size={20} strokeWidth={2.4} aria-hidden="true" />
        <p>{message.text}</p>
      </article>
    );
  }

  return null;
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

function LoadingState({ message }) {
  return <div className="roleplay-state-card">{message}</div>;
}

export default function RoleplayIngamePage({ roleplaySessionId, onBack }) {
  const [ingameData, setIngameData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [messages, setMessages] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [turnUiState, setTurnUiState] = useState(null);
  const [sessionStatus, setSessionStatus] = useState(null);
  const recorderRef = useRef(null);
  const timerRef = useRef(null);
  const audioRef = useRef(null);
  const contentScrollRef = useRef(null);
  const previousMessageCountRef = useRef(0);

  useEffect(() => {
    let isMounted = true;

    async function loadIngameData() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const payload = await getConvenienceStoreIngame();
        if (!isMounted) {
          return;
        }

        setIngameData(payload);
        const initialDialogue = payload.current_step?.character_dialogue_text;
        const initialDialogueTranslation = getTranslationText(
          payload.current_step?.character_dialogue_translation_json,
          payload.version?.default_system_language,
        );

        setMessages(
          initialDialogue
            ? [
                {
                  id: `${payload.current_step.step_id}-initial-character-dialogue`,
                  tone: 'customer',
                  ko: initialDialogue,
                  en: initialDialogueTranslation,
                  hasFeedback: false,
                },
              ]
            : [],
        );
      } catch (error) {
        if (isMounted) {
          setErrorMessage(error.message || 'Roleplay ingame data could not be loaded.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadIngameData();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    return () => {
      clearInterval(timerRef.current);
      if (recorderRef.current) {
        recorderRef.current.cancel();
      }
    };
  }, []);

  useEffect(() => {
    const content = contentScrollRef.current;
    const previousMessageCount = previousMessageCountRef.current;
    previousMessageCountRef.current = messages.length;

    if (!content || previousMessageCount === 0 || messages.length <= previousMessageCount) {
      return undefined;
    }

    const animationFrameId = requestAnimationFrame(() => {
      content.scrollTop = content.scrollHeight;
    });

    return () => cancelAnimationFrame(animationFrameId);
  }, [messages.length]);

  async function startRecording() {
    if (!ingameData) {
      setErrorMessage('Roleplay data is still loading.');
      return;
    }

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
    if (!recorderRef.current || !ingameData) {
      return;
    }
    if (!roleplaySessionId) {
      setErrorMessage('Roleplay session is not ready.');
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
      const payload = await sendRoleplaySessionTurn({
        roleplaySessionId,
        audioBlob,
        clientTurnId: crypto.randomUUID(),
      });
      const turnMessages = mapTurnMessages(payload);

      setMessages((current) => [
        ...current,
        ...(turnMessages.length
          ? turnMessages
          : [
              {
                id: crypto.randomUUID(),
                type: 'dialogue',
                tone: 'learner',
                ko: payload.transcript,
                en: 'Voice response recorded.',
                hasFeedback: Boolean(payload.feedback),
              },
              {
                id: crypto.randomUUID(),
                type: 'dialogue',
                tone: 'customer',
                ko: payload.assistant_message.ko,
                en: payload.assistant_message.en,
                hasFeedback: false,
              },
            ]),
      ]);
      setTurnUiState(payload.ui_state || null);
      setSessionStatus(payload.session_status || null);

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
  const backgroundImage = ingameData?.location?.background_image_url || FALLBACK_BACKGROUND_IMAGE;
  const step = ingameData?.current_step;
  const totalChances = ingameData?.ui_state?.total_chances || 5;
  const remainingChances = turnUiState?.remaining_chances ?? ingameData?.ui_state?.remaining_chances ?? totalChances;
  const scoreCount = turnUiState?.score_count ?? ingameData?.ui_state?.score_count ?? 0;
  const totalSteps = turnUiState?.total_steps ?? ingameData?.ui_state?.total_steps ?? 1;
  const currentStepOrder =
    turnUiState?.current_step_order ?? ingameData?.ui_state?.current_step_order ?? step?.step_order ?? 1;
  const stepLabel = turnUiState?.current_step_label || `Step ${step?.step_order || 1}: ${step?.step_title || ''}`;
  const isSessionEnded = Boolean(sessionStatus?.is_ended);
  const progressWidth = useMemo(
    () => `${Math.max(3, Math.min(100, (currentStepOrder / Math.max(totalSteps, 1)) * 100))}%`,
    [currentStepOrder, totalSteps],
  );

  return (
    <main className="app-stage roleplay-stage">
      <div className="mobile-shell roleplay-ingame-shell">
        <img className="roleplay-scene-bg" src={backgroundImage} alt="" aria-hidden="true" />
        <div className="roleplay-scene-scrim" aria-hidden="true" />

        <header className="roleplay-topbar">
          <button type="button" aria-label="Back to roleplay list" onClick={onBack}>
            <ChevronLeft size={29} strokeWidth={2.6} aria-hidden="true" />
          </button>
          <h1>{ingameData?.scenario?.title || 'Convenience Store'}</h1>
          <span className="roleplay-difficulty">{ingameData?.scenario?.difficulty || 'Easy'}</span>
          <button type="button" aria-label="Menu">
            <Menu size={30} strokeWidth={2.6} aria-hidden="true" />
          </button>
        </header>

        {isLoading ? <LoadingState message="Loading roleplay..." /> : null}
        {!isLoading && !ingameData ? <LoadingState message={errorMessage} /> : null}

        {ingameData ? (
          <>
            <section className="roleplay-step-card" aria-label="Current step">
              <div className="step-title-row">
                <span className="step-number">{formatStepNumber(step.step_order)}</span>
                <strong>{stepLabel}</strong>
              </div>
              <div className="step-progress-row">
                <span className="step-progress-track">
                  <span style={{ width: progressWidth }} />
                </span>
                <b>{`${scoreCount} / ${totalChances}`}</b>
                <div className="step-hearts" aria-label={`${remainingChances} chances remaining`}>
                  {Array.from({ length: remainingChances }).map((_, index) => (
                    <span key={index}>
                      <Heart size={24} fill="currentColor" strokeWidth={2.1} aria-hidden="true" />
                    </span>
                  ))}
                </div>
              </div>
            </section>

            {step.guidance_text ? (
              <div className="roleplay-tip">
                <span>
                  <Lightbulb size={22} strokeWidth={2.4} aria-hidden="true" />
                </span>
                {step.guidance_text}
              </div>
            ) : null}

            <section className="roleplay-content-stack" aria-label="Conversation" ref={contentScrollRef}>
              {step.scene_text ? (
                <article className="roleplay-info-card">
                  <BookOpen size={24} fill="currentColor" strokeWidth={1.8} aria-hidden="true" />
                  <p>{step.scene_text}</p>
                </article>
              ) : null}

              {step.character_action_text ? (
                <article className="roleplay-action-card">
                  <Sparkles size={26} aria-hidden="true" />
                  <p>{step.character_action_text}</p>
                </article>
              ) : null}

              {messages.map((message) =>
                message.type === 'dialogue' || !message.type ? (
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
                ) : (
                  <TurnMessageCard message={message} key={message.id} />
                ),
              )}
            </section>
          </>
        ) : null}

        {showFeedback && feedback ? (
          <FeedbackPanel feedback={feedback} onClose={() => setShowFeedback(false)} />
        ) : null}

        {errorMessage && ingameData ? <p className="roleplay-error">{errorMessage}</p> : null}

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
                <Star size={28} fill="currentColor" strokeWidth={2.5} aria-hidden="true" />
              </button>
              <div className="composer-input">
                <span>
                  {isSessionEnded
                    ? sessionStatus.end_status === 'completed'
                      ? 'Roleplay complete'
                      : 'Roleplay ended'
                    : isSending
                      ? 'Sending voice...'
                      : 'Type a message...'}
                </span>
                <button
                  type="button"
                  aria-label="Start voice recording"
                  onClick={startRecording}
                  disabled={isSending || isLoading || isSessionEnded}
                >
                  <Mic size={25} strokeWidth={2.8} aria-hidden="true" />
                </button>
              </div>
            </>
          )}
          <button
            className="composer-send"
            type="button"
            aria-label={isRecording ? 'Send voice recording' : 'Send message'}
            onClick={isRecording ? sendRecording : undefined}
            disabled={isSending || isLoading || isSessionEnded}
          >
            {isSending ? (
              <Speaker size={24} strokeWidth={2.4} aria-hidden="true" />
            ) : (
              <ArrowUp size={30} strokeWidth={2.6} aria-hidden="true" />
            )}
          </button>
        </footer>
      </div>
    </main>
  );
}

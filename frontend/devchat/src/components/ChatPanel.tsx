import { useRef, useEffect, useState } from 'react'
import type { ChatResponse, ChatCard } from '../lib/api.ts'

interface Message {
  role: 'student' | 'assistant'
  text?: string
  resp?: ChatResponse
}

interface Props {
  messages: Message[]
  onSend: (text: string) => void
  busy: boolean
}

function SourceBadges({ sources }: { sources: unknown[] }) {
  return (
    <span className="source-badges">
      {sources.map((s, i) => (
        <span key={i} className="source-badge">
          {typeof s === 'object' && s !== null && 'title' in s
            ? String((s as { title: unknown }).title)
            : `출처 ${i + 1}`}
        </span>
      ))}
    </span>
  )
}

function CardView({ card }: { card: ChatCard }) {
  const { type, title } = card

  const header = <div className="card-title">[{type}] {title}</div>

  switch (type) {
    case 'K1_GUIDE':
      return (
        <div className="chat-card k1">
          {header}
          {card.steps && (
            <ol className="card-steps">
              {card.steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
          {card.sources && card.sources.length > 0 && (
            <div className="card-sources">
              <span className="sources-label">참조: </span>
              <SourceBadges sources={card.sources} />
            </div>
          )}
        </div>
      )

    case 'K2_ANSWER':
      return (
        <div className="chat-card k2">
          {header}
          {card.answer && <div className="card-answer">{card.answer}</div>}
          {card.sources && card.sources.length > 0 && (
            <div className="card-sources">
              <span className="sources-label">출처: </span>
              <SourceBadges sources={card.sources} />
            </div>
          )}
        </div>
      )

    case 'K3_CULTURE':
      return (
        <div className="chat-card k3">
          {header}
          {card.interpretations && (
            <ul className="card-interpretations">
              {(card.interpretations as unknown[]).map((it, i) => (
                <li key={i}>
                  {typeof it === 'string' ? it : JSON.stringify(it)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )

    case 'K4_PRIVATE':
      return (
        <div className="chat-card k4">
          {header}
          {card.steps && (
            <ol className="card-steps">
              {card.steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
        </div>
      )

    case 'K5_SAFETY':
      return (
        <div className="chat-card k5">
          {header}
          {card.steps && (
            <ol className="card-steps">
              {card.steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
          {card.hotlines && card.hotlines.length > 0 && (
            <div className="card-hotlines">
              {card.hotlines.map((h, i) => (
                <div key={i} className="hotline-item">
                  <span className="hotline-label">{h.label}</span>
                  <span className="hotline-tel">{h.tel}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )

    case 'K6_QUEUE':
      return (
        <div className="chat-card k6">
          {header}
          {card.degraded && card.notice && (
            <div className="card-notice warning">{card.notice}</div>
          )}
          {card.steps && (
            <ol className="card-steps">
              {card.steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
        </div>
      )

    case 'K8_TODAY':
      return (
        <div className="chat-card k8">
          {header}
          {card.today_cards && (
            <ul className="card-list">
              {(card.today_cards as unknown[]).map((tc, i) => (
                <li key={i}>{typeof tc === 'string' ? tc : JSON.stringify(tc)}</li>
              ))}
            </ul>
          )}
        </div>
      )

    case 'K9_HANDOFF':
      return (
        <div className="chat-card k9">
          {header}
          {typeof card.message === 'string' && (
            <div className="card-answer">{card.message}</div>
          )}
        </div>
      )

    default:
      return (
        <div className="chat-card fallback">
          {header}
          <pre className="card-json">{JSON.stringify(card, null, 2)}</pre>
        </div>
      )
  }
}

export function ChatPanel({ messages, onSend, busy }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend() {
    const t = input.trim()
    if (!t || busy) return
    setInput('')
    onSend(t)
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">메시지를 입력하세요.</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            {msg.role === 'student' ? (
              <div className="bubble-text student-bubble">{msg.text}</div>
            ) : (
              <div className="bubble-assistant">
                {msg.resp ? (
                  <>
                    <CardView card={msg.resp.card} />
                    {msg.resp.bubble && (
                      <div className="bubble-text assistant-bubble">{msg.resp.bubble}</div>
                    )}
                  </>
                ) : (
                  <div className="bubble-text assistant-bubble">{msg.text}</div>
                )}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="chat-busy">응답 중...</div>}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="메시지 입력 (Enter 전송, Shift+Enter 줄바꿈)"
          rows={2}
          disabled={busy}
        />
        <button
          type="button"
          className="send-btn"
          onClick={handleSend}
          disabled={busy || !input.trim()}
        >
          전송
        </button>
      </div>
    </div>
  )
}

export type { Message }

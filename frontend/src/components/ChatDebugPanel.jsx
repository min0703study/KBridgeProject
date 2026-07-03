import { useState } from 'react';

// k_bridge_admin의 frontend/admin/chat_dev.html 디버그 패널 이관본.
// 탭 3개: 노드 트레이스 / RAG 원본 / LLM. (RAG 검색 탭은 admin 인증이 필요해 chat_dev.html에 남김.)
// data = POST /api/chat/message 응답의 data 객체 (trace, rag_sources, llm_* 포함).

const TABS = [
  { key: 'trace', label: '노드 트레이스' },
  { key: 'rag', label: 'RAG 원본' },
  { key: 'llm', label: 'LLM' },
];

function routeClass(value) {
  if (value === 'answer_card') return 'route-answer';
  if (value === 'safety') return 'route-safety';
  if (value === 'handoff' || value === 'need_review') return 'route-handoff';
  if (value === 'refuse') return 'route-refuse';
  return '';
}

function formatValue(value) {
  if (value === null || value === undefined) return 'null';
  if (value === true) return 'true';
  if (value === false) return 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function TraceTab({ trace }) {
  if (!trace?.length) {
    return <p className="chat-debug-empty">이번 응답에 트레이스 없음</p>;
  }

  return (
    <div className="chat-debug-trace-list">
      {trace.map((entry, index) => {
        const { node, ...rest } = entry || {};
        return (
          <div className="chat-debug-trace-node" key={`${node}-${index}`}>
            <div className="chat-debug-trace-name">{index + 1}. {node}</div>
            {Object.keys(rest).length ? (
              <div className="chat-debug-trace-fields">
                {Object.entries(rest).map(([key, value]) => (
                  <div className="chat-debug-trace-field" key={key}>
                    <span className="chat-debug-trace-key">{key}</span>
                    <span className={`chat-debug-trace-val ${key === 'route' ? routeClass(value) : ''}`}>
                      {formatValue(value)}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function RagTab({ sources }) {
  if (!sources?.length) {
    return <p className="chat-debug-empty">이번 응답에 RAG 인용 없음 (키워드 매칭 또는 임베딩 미빌드)</p>;
  }

  return (
    <div className="chat-debug-rag-list">
      {sources.map((chunk, index) => (
        <div className="chat-debug-rag-chunk" key={chunk?.chunk_id || index}>
          <div className="chat-debug-rag-header">
            <span className="chat-debug-rag-title">{chunk?.title || '(제목 없음)'}</span>
            <span className="chat-debug-rag-score">
              {chunk?.score != null ? Number(chunk.score).toFixed(3) : '—'}
            </span>
          </div>
          <div className="chat-debug-rag-id">{chunk?.chunk_id || ''}</div>
          <div className="chat-debug-rag-text">{chunk?.text_ko || ''}</div>
        </div>
      ))}
    </div>
  );
}

function LlmTab({ data }) {
  const rows = [
    ['provider', data.llm_provider ?? '—'],
    ['calls', data.llm_calls ?? '—'],
    ['fallback', data.llm_fallback_used ? 'yes' : 'no'],
    [
      'est. cost USD',
      data.llm_estimated_cost_usd != null ? `$${Number(data.llm_estimated_cost_usd).toFixed(5)}` : '—',
    ],
    ['route', data.route ?? '—'],
    ['risk_level', data.risk_level ?? '—'],
  ];

  return (
    <div className="chat-debug-llm-grid">
      {rows.map(([label, value]) => (
        <div className="chat-debug-llm-row" key={label}>
          <span className="chat-debug-llm-label">{label}</span>
          <span
            className={`chat-debug-llm-value ${
              label === 'fallback' ? (value === 'yes' ? 'warn' : 'ok') : ''
            }`}
          >
            {String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ChatDebugPanel({ data, onClose }) {
  const [activeTab, setActiveTab] = useState('trace');

  return (
    <aside className="chat-debug-panel" aria-label="Chat debug panel">
      <div className="chat-debug-tabs">
        {TABS.map((tab) => (
          <button
            className={`chat-debug-tab ${activeTab === tab.key ? 'is-active' : ''}`}
            type="button"
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
        <span className="chat-debug-spacer" />
        <button className="chat-debug-close" type="button" onClick={onClose} aria-label="Close debug panel">
          ✕
        </button>
      </div>
      <div className="chat-debug-content">
        {!data ? (
          <p className="chat-debug-empty">메시지를 보내면 디버그 정보가 표시됩니다.</p>
        ) : activeTab === 'trace' ? (
          <TraceTab trace={data.trace} />
        ) : activeTab === 'rag' ? (
          <RagTab sources={data.rag_sources} />
        ) : (
          <LlmTab data={data} />
        )}
      </div>
    </aside>
  );
}

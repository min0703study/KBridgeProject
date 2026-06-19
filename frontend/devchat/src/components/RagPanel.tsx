import type { RagSource } from '../lib/api.ts'

interface Props {
  sources: RagSource[]
}

const MAX_TEXT = 200

function truncate(text: string): string {
  return text.length > MAX_TEXT ? text.slice(0, MAX_TEXT) + '…' : text
}

export function RagPanel({ sources }: Props) {
  if (sources.length === 0) {
    return (
      <div className="rag-panel">
        <div className="panel-header">RAG 출처</div>
        <div className="panel-empty">이번 턴 RAG 참조 없음</div>
      </div>
    )
  }

  const sorted = [...sources].sort((a, b) => b.score - a.score)

  return (
    <div className="rag-panel">
      <div className="panel-header">RAG 출처 ({sources.length}개)</div>
      <ul className="rag-list">
        {sorted.map((src) => (
          <li key={src.chunk_id} className="rag-item">
            <div className="rag-item-header">
              <span className="rag-title">{src.title}</span>
              <span className="rag-score">{src.score.toFixed(3)}</span>
            </div>
            <div className="rag-text">{truncate(src.text_ko)}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}

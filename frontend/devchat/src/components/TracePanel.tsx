import type { TraceStep } from '../lib/api.ts'

interface Props {
  trace: TraceStep[]
}

function isHighlighted(step: TraceStep): boolean {
  if (step.degraded === true) return true
  if (step.node === 'risk_gate' && typeof step.risk === 'number' && step.risk >= 2) return true
  return false
}

function ChipValue({ v }: { v: unknown }) {
  if (v === null || v === undefined) return <span className="chip-val">—</span>
  if (typeof v === 'boolean') return <span className="chip-val">{v ? 'true' : 'false'}</span>
  if (typeof v === 'object') return <span className="chip-val">{JSON.stringify(v)}</span>
  return <span className="chip-val">{String(v)}</span>
}

export function TracePanel({ trace }: Props) {
  if (trace.length === 0) {
    return (
      <div className="trace-panel">
        <div className="panel-header">노드 트레이스</div>
        <div className="panel-empty">트레이스 없음 — 메시지를 보내면 노드 경로가 여기 표시됩니다.</div>
      </div>
    )
  }

  return (
    <div className="trace-panel">
      <div className="panel-header">노드 트레이스 ({trace.length}스텝)</div>
      <ol className="trace-list">
        {trace.map((step, i) => {
          const { node, ...rest } = step
          const highlight = isHighlighted(step)
          return (
            <li key={i} className={`trace-step${highlight ? ' trace-highlight' : ''}`}>
              <span className="trace-node">{node}</span>
              <span className="trace-chips">
                {Object.entries(rest).map(([k, v]) => (
                  <span key={k} className="trace-chip">
                    <span className="chip-key">{k}=</span>
                    <ChipValue v={v} />
                  </span>
                ))}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

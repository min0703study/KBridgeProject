import React from 'react'
import { CheckCircle2, CircleAlert, HelpCircle, RotateCcw, Sparkles, XCircle } from 'lucide-react'

const statusIcon = {
  Strong: CheckCircle2,
  'Keep Practicing': Sparkles,
  'Needs Review': CircleAlert,
}

function focusItemSizeClass(item) {
  const length = String(item ?? '').replace(/\s+/g, '').length

  if (length >= 9) return 'focus-item-long'
  if (length >= 6) return 'focus-item-medium'
  return 'focus-item-short'
}

export default function ResultsView({ summary, reviewItems, evaluations, onDone }) {
  const nextFocus = evaluations.flatMap((evaluation) => evaluation.review_items)
  const uniqueFocus = [...new Set(nextFocus)]
  const stats = [
    { label: 'Correct', value: summary.correct, Icon: CheckCircle2, tone: 'correct' },
    { label: 'Incorrect', value: summary.incorrect, Icon: XCircle, tone: 'incorrect' },
    { label: 'Not sure yet', value: summary.dontKnow, Icon: HelpCircle, tone: 'unsure' },
    { label: 'Need review', value: summary.needsReview, Icon: RotateCcw, tone: 'review' },
  ]

  return (
    <main className="screen results-screen">
      <div className="result-page-title">
        <span className="result-status-pill">Today’s AI result</span>
      </div>
      <section className="hero-panel compact">
        <div className="result-hero-copy">
          <div className="result-score-line">
            <strong>{summary.correct}</strong>
            <span>/ {summary.total} correct</span>
          </div>
        </div>
        <div className="result-stat-grid">
          {stats.map(({ label, value, Icon, tone }) => (
            <span className={`result-stat-card ${tone}`} key={label}>
              <span className="result-stat-icon"><Icon size={20} /></span>
              <span className="result-stat-copy">
                <strong>{value}</strong>
                <small>{label}</small>
              </span>
            </span>
          ))}
        </div>
      </section>

      <section className="skill-result-list">
        {evaluations.map((evaluation) => {
          const Icon = statusIcon[evaluation.status]
          return (
            <article className="review-card skill-result-card" key={evaluation.skill}>
              <Icon size={24} />
              <div>
                <h2>{evaluation.skill}</h2>
                <p>{evaluation.failure_count} item{evaluation.failure_count === 1 ? '' : 's'} to review</p>
              </div>
              <span className={`skill-status ${evaluation.status.toLowerCase().replaceAll(' ', '-')}`}>
                {evaluation.status}
              </span>
            </article>
          )
        })}
      </section>

      <section className="review-card next-focus-card">
        <h2>Next Review Focus</h2>
        {uniqueFocus.length ? (
          <div className="chip-row next-focus-grid">
            {uniqueFocus.map((item) => (
              <span className={focusItemSizeClass(item)} key={item}>{item}</span>
            ))}
          </div>
        ) : (
          <p className="meaning">No extra review is needed today.</p>
        )}
        <p className="ready-copy">
          {uniqueFocus.length
            ? 'Your personalized review will be ready on the home screen.'
            : 'Your next regular Daily Practice is ready whenever you are.'}
        </p>
      </section>

      <button className="primary-button wide" onClick={onDone} type="button">Done</button>
    </main>
  )
}

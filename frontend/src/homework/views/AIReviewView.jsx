import React from 'react'
import { Bot, CheckCircle2, CircleAlert, Sparkles } from 'lucide-react'

const statusIcon = {
  Strong: CheckCircle2,
  'Keep Practicing': Sparkles,
  'Needs Review': CircleAlert,
}

export default function AIReviewView({ evaluations, reviewItems, onDone }) {
  const nextFocus = evaluations.flatMap((evaluation) => evaluation.review_items)
  const uniqueFocus = [...new Set(nextFocus)]

  return (
    <main className="screen ai-review-screen">
      <section className="hero-panel ai-review-hero">
        <div className="ai-icon"><Bot size={34} /></div>
        <p className="eyebrow">AI Review Result</p>
        <h1>Ko-pilot checked today’s practice.</h1>
        <p>
          {reviewItems.length
            ? 'Let’s strengthen a few items in your next personalized review.'
            : 'You showed strong understanding across today’s practice.'}
        </p>
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
          <div className="chip-row">{uniqueFocus.map((item) => <span key={item}>{item}</span>)}</div>
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

import React from 'react'
import { CheckCircle2, HelpCircle, RotateCcw, XCircle } from 'lucide-react'

function reviewGroups(reviewItems) {
  return reviewItems.reduce((groups, { question }) => {
    const key = question.evaluation_skill
    groups[key] = groups[key] ?? []
    groups[key].push(question.review_label ?? question.target_item)
    return groups
  }, {})
}

export default function ResultsView({ summary, reviewItems, onContinue }) {
  const groups = reviewGroups(reviewItems)

  return (
    <main className="screen results-screen">
      <section className="hero-panel compact">
        <p className="eyebrow">Today’s Review Result</p>
        <h1>{summary.correct}/{summary.total} correct</h1>
        <p>Great work. Ko-pilot is checking what to review next.</p>
        <div className="result-stat-grid">
          <span><CheckCircle2 size={24} /><strong>{summary.correct}</strong> Correct</span>
          <span><XCircle size={24} /><strong>{summary.incorrect}</strong> Incorrect</span>
          <span><HelpCircle size={24} /><strong>{summary.dontKnow}</strong> Not sure yet</span>
          <span><RotateCcw size={24} /><strong>{summary.needsReview}</strong> Need review</span>
        </div>
      </section>

      <section className="generated-list">
        <h2 className="section-title">Review again next time</h2>
        {Object.keys(groups).length === 0 ? (
          <article className="review-card">
            <h2>No review items today</h2>
            <p className="meaning">All six learning skills were completed without a miss.</p>
          </article>
        ) : Object.entries(groups).map(([skill, items]) => (
          <article className="review-card" key={skill}>
            <p className="eyebrow">{skill}</p>
            <div className="chip-row">
              {[...new Set(items)].map((item) => <span key={item}>{item}</span>)}
            </div>
          </article>
        ))}
      </section>

      <button className="primary-button wide" onClick={onContinue} type="button">View AI Review Result</button>
    </main>
  )
}

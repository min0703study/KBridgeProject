import React from 'react'
import { BookOpen, ChevronLeft } from 'lucide-react'
import { getUnitAssets } from '../assets/unitAssets'

export function StatusBar() {
  return null
}

export function BackButton({ label = 'Back' }) {
  return (
    <button className="back-button" aria-label={label} type="button">
      <ChevronLeft size={36} strokeWidth={2.4} />
    </button>
  )
}

export function WeatherIllustration({ compact = false, unitId = 'unit_07' }) {
  const assets = getUnitAssets(unitId)

  return (
    <div className={`weather-art ${compact ? 'compact' : ''}`} aria-hidden="true">
      <img src={assets.headerIcon} alt="" />
    </div>
  )
}

export function LessonProgress({ unit, current, total }) {
  const lessonNumber = unit.unit_id.replace('unit_', '').padStart(2, '0')
  const title = unit.unit_title.replace(/^Unit \d+\.\s*/, '')

  return (
    <section className="lesson-progress-card">
      <WeatherIllustration compact unitId={unit.unit_id} />
      <div className="lesson-progress-copy">
        <div className="lesson-pill">
          <BookOpen aria-hidden="true" />
          <strong>Lesson {lessonNumber}</strong>
        </div>
        <span className="lesson-progress-title">{title}</span>
      </div>
      <div className="ring-progress" style={{ '--progress': `${total ? (current / total) * 100 : 0}%` }}>
        <span aria-label={`${current} of ${total}`}>
          <strong>{current}</strong>
          <small>/ {total}</small>
        </span>
      </div>
    </section>
  )
}

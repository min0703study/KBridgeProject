import React from 'react'
import { LessonProgress } from './AppChrome'

export default function ProgressHeader({ unit, step, current, total }) {
  return (
    <header className="progress-header" aria-label={step}>
      <LessonProgress unit={unit} current={current} total={total} />
    </header>
  )
}

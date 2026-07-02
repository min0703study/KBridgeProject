import React from 'react'
import { BookOpen, Clock, Flag } from 'lucide-react'
import { BackButton, StatusBar } from '../components/AppChrome'
import { getUnitAssets } from '../assets/unitAssets'
import { SemanticText } from '../utils/koreanText.jsx'

export default function ReviewIntro({ unit, total, onStart }) {
  const lessonNumber = unit.unit_id.replace('unit_', '').padStart(2, '0')
  const title = unit.unit_title.replace(/^Unit \d+\.\s*/, '')
  const assets = getUnitAssets(unit.unit_id)
  const isUnitOne = unit.unit_id === 'unit_01'
  const introCopy = isUnitOne ? <>Review greetings, self-introduction, nationality,<br />and jobs.</> : unit.unit_goal
  const totalDisplay = total
  const stepsDisplay = isUnitOne ? 4 : 3
  const timeDisplay = isUnitOne ? 10 : unit.estimated_time_min

  return (
    <main className="screen intro-screen">
      <StatusBar />
      <BackButton />
      <section className="page-title">
        <h1>Daily Practice</h1>
        <p>A quick preview of today’s lesson.</p>
      </section>

      <section className={`lesson-preview-card unit-intro-${unit.unit_id}`}>
        <div className="lesson-badge sage">Lesson {lessonNumber}</div>
        <SemanticText as="h2" text={title} />
        {isUnitOne ? <strong className="intro-english-title">Hello</strong> : null}
        <p>{introCopy}</p>
        <img className={`preview-art asset-illustration unit-preview-${unit.unit_id}`} src={assets.introHero} alt="" />
      </section>

      <section className="glance-card">
        <h3>Review at a glance</h3>
        <div className="mini-stats">
          <span><BookOpen size={28} /> <strong>{totalDisplay}</strong> questions</span>
          <span><Flag size={28} /> <strong>{stepsDisplay}</strong> learning steps</span>
          <span><Clock size={28} /> <strong>{timeDisplay}</strong> min</span>
        </div>
      </section>

      <button className="primary-button wide" onClick={onStart} type="button">Start Review</button>
    </main>
  )
}

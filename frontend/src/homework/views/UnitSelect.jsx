import React from 'react'
import { ArrowRight } from 'lucide-react'
import { StatusBar } from '../components/AppChrome'
import smallSun from '../assets/daily-practice-ui/small-sun.png'
import { getUnitAssets } from '../assets/unitAssets'
import { SemanticText } from '../utils/koreanText.jsx'

function unitDisplayTitle(unit) {
  return unit.unit_title.replace(/^Unit \d+\.\s*/, '')
}

function unitEnglishTitle(unit) {
  return unit.unit_english_title ?? unit.vocabulary_list[0]?.english_meaning ?? 'Daily Practice'
}

export default function UnitSelect({ units, personalizedCount, onStart, onStartPersonalized }) {
  const featured = units.find((unit) => unit.unit_id === 'unit_01') ?? units[0]
  const featuredAssets = getUnitAssets(featured.unit_id)
  const lessonNumber = featured.unit_id.replace('unit_', '').padStart(2, '0')
  const moreLessons = units.filter((unit) => unit.unit_id !== featured.unit_id).slice(0, 4)

  return (
    <main className="screen cover-screen">
      <StatusBar />
      <section className="cover-greeting">
        <img className="morning-sun-img" src={smallSun} alt="" />
        <h1>Good morning,<br />Maria!</h1>
        <p>Let’s review today’s Korean lesson.</p>
      </section>

      <section className="featured-lesson-card">
        <div className="lesson-badge">Lesson {lessonNumber}</div>
        <div className="featured-copy">
          <SemanticText as="h2" text={unitDisplayTitle(featured)} />
          <strong>{unitEnglishTitle(featured)}</strong>
        </div>
        <img className={`people-illustration asset-illustration unit-hero-${featured.unit_id}`} src={featuredAssets.hero} alt="" />
        {personalizedCount > 0 ? (
          <button className="personalized-ready" onClick={onStartPersonalized} type="button">
            <span>Personalized Review Ready</span>
            <strong>{personalizedCount} focus items</strong>
          </button>
        ) : null}
        <button className="primary-button cover-cta" onClick={onStart} type="button">
          Start Review
        </button>
      </section>

      <section className="more-lessons-head">
        <h2>More lessons</h2>
        <button type="button">View all <ArrowRight size={22} /></button>
      </section>

      <section className="lesson-carousel" aria-label="More lessons">
        {moreLessons.map((unit) => {
          const assets = getUnitAssets(unit.unit_id)

          return (
          <button className="mini-lesson-card" key={unit.unit_id} type="button">
            <span className="mini-lesson-badge">Lesson {unit.unit_id.replace('unit_', '').padStart(2, '0')}</span>
            <img className="mini-lesson-asset" src={assets.miniIcon} alt="" />
            <SemanticText as="strong" text={unitDisplayTitle(unit)} />
            <small>{unitEnglishTitle(unit)}</small>
          </button>
        )})}
      </section>
      <div className="pager-dots" aria-hidden="true"><span className="active" /><span /><span /><span /></div>
    </main>
  )
}

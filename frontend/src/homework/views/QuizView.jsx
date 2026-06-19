import React from 'react'
import { BackButton, StatusBar } from '../components/AppChrome'
import ProgressHeader from '../components/ProgressHeader'
import QuestionCard from '../components/QuestionCard'

export default function QuizView(props) {
  const { unit, currentIndex, total, question, isPersonalized } = props

  return (
    <main className="screen quiz-screen">
      <StatusBar />
      <BackButton />
      <ProgressHeader unit={unit} step={isPersonalized ? 'Personalized Review' : 'Practice'} current={currentIndex + 1} total={total} />
      <QuestionCard question={question} {...props} isLast={currentIndex + 1 === total} />
    </main>
  )
}

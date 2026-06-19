import React from 'react'
import { BookOpen, CheckCircle2, HelpCircle, MessageCircle, Target, XCircle } from 'lucide-react'
import BlockOrder from './BlockOrder'
import { getUnitAssets } from '../assets/unitAssets'
import { SemanticText } from '../utils/koreanText.jsx'

function questionTitle(question) {
  const titles = {
    word_meaning_choice: 'Choose the meaning',
    korean_word_choice: 'Choose the Korean word',
    context_fill_choice: 'Complete the sentence',
    grammar_ending_choice: 'Choose the ending',
    sentence_structure_choice: 'Build the sentence',
    sentence_order: 'Arrange the sentence',
    reading_choice: 'Read and answer',
    situation_expression_choice: 'Choose the expression',
  }
  return titles[question.question_type] ?? 'Daily Practice'
}

export default function QuestionCard({ question, answer, setAnswer, checked, grade, onCheck, onDontKnow, onNext, isLast }) {
  const isChoice = Boolean(question.choices?.length)
  const isOrder = Boolean(question.blocks?.length)
  const isMeaningChoice = question.question_type === 'word_meaning_choice'
  const isKoreanChoice = question.question_type === 'korean_word_choice'
  const isReading = question.question_type === 'reading_choice'
  const isSituationExpression = question.question_type === 'situation_expression_choice'
  const isSituation = Boolean(question.situation)
  const sourceQuestionId = question.source_question_id ?? question.question_id
  const isRevisedUnitOne = question.unit_id === 'unit_01'
  const showRomanization = !isRevisedUnitOne
  const showSentenceEnglish = !isRevisedUnitOne || ['u01_q13', 'u01_q15'].includes(sourceQuestionId)
  const showSentenceFocus = !isReading && !isOrder && !isSituationExpression
  const isSentenceSupportRemoved = !showRomanization && !showSentenceEnglish
  const assets = getUnitAssets(question.unit_id)
  const feedbackCorrectAnswer = Array.isArray(question.correct_answer)
    ? question.correct_answer.join(' ')
    : isRevisedUnitOne
      ? String(question.correct_answer).split('/')[0].trim()
      : question.correct_answer

  return (
    <section className={`question-card ${isOrder ? 'order-question' : 'choice-question'} ${isReading ? 'reading-question' : ''} ${isRevisedUnitOne ? 'revised-unit-one-question' : ''}`}>
      <div className="question-hero">
        <div className="question-art" aria-hidden="true">
          <img src={isOrder ? assets.orderArt : assets.questionArt} alt="" />
        </div>
        <div className="question-copy">
          <div className="mode-dot"><Target size={22} /></div>
          <h2>{questionTitle(question)}</h2>
          <p>{question.prompt}</p>
          {isSituation ? <p className="situation-copy">{question.situation}</p> : null}
          {isMeaningChoice ? (
            <>
              {showRomanization && question.romanization ? <p className="romanization big">{question.romanization}</p> : null}
              <SemanticText
                as="strong"
                className={`korean-display ${showRomanization ? '' : 'support-removed'}`}
                singleLine={isRevisedUnitOne}
                text={question.korean}
              />
            </>
          ) : isKoreanChoice ? (
            <strong className="inline-focus">{question.english_meaning}</strong>
          ) : showSentenceFocus ? (
            <div className={`sentence-focus ${isSentenceSupportRemoved ? 'support-removed' : ''}`}>
              {isSentenceSupportRemoved
                ? <strong className="sentence-korean-line">{question.korean}</strong>
                : <SemanticText as="strong" text={question.korean} />}
              {showRomanization && question.romanization ? <small>{question.romanization}</small> : null}
              {showSentenceEnglish && question.english_meaning ? <span>{question.english_meaning}</span> : null}
            </div>
          ) : null}
        </div>
      </div>

      {isReading ? (
        <div className="reading-passage">
          {question.passage.map((line, index) => (
            <div className={`passage-line ${isRevisedUnitOne ? 'support-removed' : ''}`} key={`${line.korean}-${index}`}>
              {isRevisedUnitOne
                ? <strong className="reading-korean-line">{line.korean}</strong>
                : <SemanticText as="strong" text={line.korean} />}
              {showRomanization && line.romanization ? <small>{line.romanization}</small> : null}
              {!isRevisedUnitOne && line.english ? <span>{line.english}</span> : null}
            </div>
          ))}
          <p className="reading-question-prompt">{question.prompt}</p>
        </div>
      ) : null}

      {isChoice ? (
        <div className="choice-grid">
          {question.choices.map((choice, index) => {
            const [korean, romanization] = String(choice).split('/').map((item) => item?.trim())
            const normalizedCorrectAnswer = Array.isArray(question.correct_answer)
              ? question.correct_answer.join(' ')
              : String(question.correct_answer)
            const isCorrectChoice = checked && String(choice) === normalizedCorrectAnswer
            const isIncorrectChoice = checked && answer === choice && !grade.is_correct
            return (
              <button
                className={`choice ${answer === choice ? 'active' : ''} ${isCorrectChoice ? 'correct-choice' : ''} ${isIncorrectChoice ? 'incorrect-choice' : ''}`}
                disabled={checked}
                key={choice}
                onClick={() => setAnswer(choice)}
                type="button"
              >
                <span className="choice-number">{index + 1}</span>
                {isKoreanChoice && romanization && showRomanization ? <small>{romanization}</small> : null}
                {isKoreanChoice || /[가-힣]/.test(korean)
                  ? <SemanticText as="strong" singleLine={isRevisedUnitOne} text={korean} />
                  : <strong>{choice}</strong>}
              </button>
            )
          })}
        </div>
      ) : null}

      {isOrder ? (
        <>
          <div className="meaning-strip">
            <MessageCircle size={32} />
            <span><small>English meaning</small><strong>{question.english_meaning}</strong></span>
          </div>
          <BlockOrder blocks={question.blocks} selected={Array.isArray(answer) ? answer : []} onChange={setAnswer} disabled={checked} />
          <div className="tip-strip"><BookOpen size={24} /><span>Grammar focus: natural word order</span></div>
        </>
      ) : null}

      {checked ? (
        <div className={`feedback ${grade.is_correct ? 'correct' : 'incorrect'} ${grade.is_dont_know ? 'dont-know' : ''}`}>
          <span className="feedback-icon" aria-hidden="true">
            {grade.is_correct ? <CheckCircle2 size={21} /> : grade.is_dont_know ? <HelpCircle size={21} /> : <XCircle size={21} />}
          </span>
          <span className="feedback-copy">
            <strong>
              {grade.is_correct
                ? 'Correct. Nice recall.'
                : grade.is_dont_know
                  ? 'No problem. Let’s review it together.'
                  : 'Not quite. Check the answer below.'}
            </strong>
            <span className="feedback-answer">
              <small>Correct answer</small>
              <b>{feedbackCorrectAnswer}</b>
            </span>
          </span>
        </div>
      ) : null}

      <div className="action-row">
        {!checked ? (
          <>
            <button className="secondary-button dont-know-button" onClick={onDontKnow} type="button">
              I don’t know yet
            </button>
            <button className="primary-button" disabled={!answer || (Array.isArray(answer) && answer.length === 0)} onClick={onCheck} type="button">
              Check Answer
            </button>
          </>
        ) : (
          <button className="primary-button" onClick={onNext} type="button">
            {isLast ? 'Review Items' : 'Next'}
          </button>
        )}
      </div>
    </section>
  )
}

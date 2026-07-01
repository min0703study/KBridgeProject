import React, { useEffect, useRef, useState } from 'react'
import { CheckCircle2, HelpCircle, MessageCircle, Target, Volume2, XCircle } from 'lucide-react'
import BlockOrder from './BlockOrder'
import { getUnitAssets } from '../assets/unitAssets'
import { SemanticText } from '../utils/koreanText.jsx'

function questionTitle(question) {
  if (question.question_type === 'korean_word_choice') {
    return (
      <>
        Choose the
        <br />
        Korean word
      </>
    )
  }

  const titles = {
    word_meaning_choice: 'Choose the meaning',
    context_fill_choice: 'Complete the sentence',
    grammar_ending_choice: 'Choose the ending',
    sentence_structure_choice: 'Build the sentence',
    sentence_order: 'Arrange the sentence',
    reading_choice: 'Read and answer',
    situation_expression_choice: 'Choose the expression',
    listening_card_choice: 'Listen and choose',
    listening_response_choice: 'Listen and answer',
    listening_sentence_choice: 'Listen and choose',
  }
  return titles[question.question_type] ?? 'Daily Practice'
}

const mockWaveform = [18, 30, 12, 40, 24, 34, 16, 28, 12, 22, 36, 18, 14, 10, 26, 12, 18, 32, 14, 12, 18, 10, 16, 12, 20, 14, 12, 16]

function choiceTextSizeClass(text) {
  const normalized = String(text ?? '').split('/')[0].trim()
  const compactLength = normalized.replace(/\s+/g, '').length
  const wordCount = normalized.split(/\s+/).filter(Boolean).length

  if (compactLength >= 13 || wordCount >= 4) return 'choice-text-sentence'
  if (compactLength >= 9 || wordCount >= 3) return 'choice-text-long'
  if (compactLength >= 6 || wordCount >= 2) return 'choice-text-medium'
  return 'choice-text-short'
}

function sentenceTextSizeClass(text) {
  const normalized = String(text ?? '').trim()
  const compactLength = normalized.replace(/\s+/g, '').length
  const spacingWeight = (normalized.match(/\s/g) ?? []).length * 0.7
  const blankWeight = (normalized.match(/_/g) ?? []).length * 0.45
  const visualLength = compactLength + spacingWeight + blankWeight

  if (visualLength >= 17) return 'sentence-text-xlong'
  if (visualLength >= 12) return 'sentence-text-long'
  if (visualLength >= 8) return 'sentence-text-medium'
  return 'sentence-text-short'
}

function situationTextSizeClass(text) {
  const length = String(text ?? '').replace(/\s+/g, '').length

  if (length >= 29) return 'situation-text-long'
  if (length >= 22) return 'situation-text-medium'
  return 'situation-text-short'
}

function splitDialogueLine(text) {
  const match = String(text ?? '').match(/^([^:：]{1,12})[:：]\s*(.+)$/)

  return match
    ? { speaker: match[1], content: match[2] }
    : { speaker: '', content: String(text ?? '') }
}

function dialogueTextSizeClass(text) {
  const length = String(text ?? '').replace(/\s+/g, '').length

  if (length >= 26) return 'dialogue-text-xlong'
  if (length >= 19) return 'dialogue-text-long'
  if (length >= 13) return 'dialogue-text-medium'
  return 'dialogue-text-short'
}

function primaryAnswer(answer) {
  return Array.isArray(answer)
    ? answer.join(' ')
    : String(answer ?? '').split('/')[0].trim()
}

function fillBlank(text, answer) {
  const value = primaryAnswer(answer)
  return String(text ?? '').replace(/_{2,}/g, value)
}

function feedbackSupport(question) {
  if (question.question_type?.startsWith('listening_')) {
    return {
      label: 'Audio script',
      korean: question.korean,
      romanization: question.romanization,
      english: question.english_meaning,
    }
  }

  const correct = primaryAnswer(question.correct_answer)
  const korean = question.question_type === 'word_meaning_choice'
    ? question.korean
    : question.question_type === 'korean_word_choice'
      ? correct
      : question.blocks?.length
        ? question.korean
        : fillBlank(question.korean, correct)

  const romanization = question.question_type === 'korean_word_choice'
    ? String(question.correct_answer ?? '').split('/')[1]?.trim()
    : question.feedback_romanization
      ? question.feedback_romanization
      : question.romanization && !String(question.romanization).includes('___')
      ? question.romanization
      : null

  const english = question.feedback_english ?? question.english_meaning ?? question.english

  if (!korean && !romanization && !english) return null

  return { korean, romanization, english }
}

export default function QuestionCard({ question, answer, setAnswer, checked, grade, onCheck, onDontKnow, onNext, isLast }) {
  const cardRef = useRef(null)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const isChoice = Boolean(question.choices?.length)
  const isOrder = Boolean(question.blocks?.length)
  const isMeaningChoice = question.question_type === 'word_meaning_choice'
  const isKoreanChoice = question.question_type === 'korean_word_choice'
  const isReading = question.question_type === 'reading_choice'
  const isListening = question.question_type?.startsWith('listening_')
  const isSituationExpression = question.question_type === 'situation_expression_choice'
  const isSituation = Boolean(question.situation)
  const sourceQuestionId = question.source_question_id ?? question.question_id
  const isRevisedUnitOne = question.unit_id === 'unit_01'
  const showRomanization = !isRevisedUnitOne
  const showSentenceEnglish = !isRevisedUnitOne || ['u01_q10', 'u01_q13', 'u01_q15'].includes(sourceQuestionId)
  const showSentenceFocus = !isReading && !isOrder && !isSituationExpression && !isListening
  const isSentenceSupportRemoved = !showRomanization && !showSentenceEnglish
  const sentenceSizeClass = sentenceTextSizeClass(question.korean)
  const assets = getUnitAssets(question.unit_id)
  const feedbackCorrectAnswer = Array.isArray(question.correct_answer)
    ? question.correct_answer.join(' ')
    : isRevisedUnitOne && !isListening
      ? String(question.correct_answer).split('/')[0].trim()
      : question.correct_answer
  const support = feedbackSupport(question)
  const visibleSupport = support && isOrder
    ? { ...support, korean: null }
    : support
  const dialogueFeedback = question.feedback_dialogue && Array.isArray(question.passage)
    ? question.passage.map((line) => {
      const dialogue = splitDialogueLine(line.korean)
      return {
        speaker: dialogue.speaker,
        korean: dialogue.content,
        romanization: splitDialogueLine(line.romanization).content,
        english: splitDialogueLine(line.english).content,
      }
    })
    : []
  const displayedOrderAnswer = isOrder && checked && Array.isArray(question.correct_answer)
    ? question.correct_answer
    : Array.isArray(answer)
      ? answer
      : []

  const gradeClass = checked
    ? grade.is_correct
      ? 'is-correct'
      : grade.is_dont_know
        ? 'is-dont-know'
        : 'is-incorrect'
    : ''

  useEffect(() => {
    cardRef.current?.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [checked, question.question_id])

  useEffect(() => {
    setIsAudioPlaying(false)
  }, [question.question_id])

  return (
    <section ref={cardRef} className={`question-card ${isOrder ? 'order-question' : 'choice-question'} question-type-${question.question_type} ${isReading ? 'reading-question' : ''} ${isListening ? 'listening-question' : ''} ${isRevisedUnitOne ? 'revised-unit-one-question' : ''} ${checked ? 'is-checked' : ''} ${gradeClass}`}>
      <div className="question-hero">
        <div className="question-art" aria-hidden="true">
          <img src={isOrder ? assets.orderArt : assets.questionArt} alt="" />
        </div>
        <div className="question-copy">
          <div className="mode-dot"><Target size={22} /></div>
          <h2>{questionTitle(question)}</h2>
          {isSituation ? (
            <p className={`situation-copy ${situationTextSizeClass(question.situation)}`}>
              {question.situation}
            </p>
          ) : null}
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
              <strong className={`sentence-korean-line ${sentenceSizeClass}`} lang="ko">
                {question.korean}
              </strong>
              {showRomanization && question.romanization ? <small>{question.romanization}</small> : null}
              {showSentenceEnglish && question.english_meaning ? <span>{question.english_meaning}</span> : null}
            </div>
          ) : null}
        </div>
      </div>

      {isReading ? (
        <div className="reading-passage">
          {question.passage.map((line, index) => {
            const dialogue = splitDialogueLine(line.korean)

            return (
              <div
                className={`passage-line ${dialogue.speaker ? 'dialogue-line' : ''} ${dialogue.speaker === 'B' ? 'speaker-b' : ''} ${isRevisedUnitOne ? 'support-removed' : ''}`}
                key={`${line.korean}-${index}`}
              >
                {dialogue.speaker ? <b className="dialogue-speaker">{dialogue.speaker}</b> : null}
                {isRevisedUnitOne
                  ? <strong className={`reading-korean-line ${dialogueTextSizeClass(dialogue.content)}`}>{dialogue.content}</strong>
                  : <SemanticText as="strong" text={dialogue.content} />}
                {showRomanization && line.romanization ? <small>{line.romanization}</small> : null}
                {!isRevisedUnitOne && line.english ? <span>{line.english}</span> : null}
              </div>
            )
          })}
          <p className="reading-question-prompt">{question.prompt}</p>
        </div>
      ) : null}

      {isListening ? (
        <div className={`listening-panel ${checked ? 'is-revealed' : ''}`}>
          <div className={`audio-player ${isAudioPlaying ? 'is-playing' : ''}`}>
            <button
              className="speaker-button"
              type="button"
              aria-label={isAudioPlaying ? 'Pause listening prompt' : 'Play listening prompt'}
              aria-pressed={isAudioPlaying}
              onClick={() => setIsAudioPlaying((value) => !value)}
            >
              <Volume2 size={30} />
            </button>
            <div className="audio-waveform" aria-hidden="true">
              {mockWaveform.map((height, index) => (
                <span
                  className={index === 12 ? 'wave-dot' : ''}
                  key={`${height}-${index}`}
                  style={{ '--wave-height': `${height}px` }}
                />
              ))}
            </div>
            <span className="audio-duration">0:06</span>
          </div>
        </div>
      ) : null}

      {isChoice ? (
        <div className="choice-grid">
          {question.choices.map((choice, index) => {
            const [korean, romanization] = String(choice).split('/').map((item) => item?.trim())
            const choiceSizeClass = choiceTextSizeClass(korean)
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
                  ? <strong className={`choice-text ${choiceSizeClass}`} lang="ko">{korean}</strong>
                  : <strong className={`choice-text ${choiceSizeClass}`}>{choice}</strong>}
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
          <BlockOrder blocks={question.blocks} selected={displayedOrderAnswer} onChange={setAnswer} disabled={checked} />
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
            {visibleSupport ? (
              <span className="feedback-support">
                {visibleSupport.label ? <small>{visibleSupport.label}</small> : null}
                {visibleSupport.korean ? <strong lang="ko">{visibleSupport.korean}</strong> : null}
                {visibleSupport.romanization ? <em>{visibleSupport.romanization}</em> : null}
                {visibleSupport.english ? <span>{visibleSupport.english}</span> : null}
              </span>
            ) : null}
            {dialogueFeedback.length ? (
              <span className="feedback-dialogue">
                <small>Dialogue meaning</small>
                {dialogueFeedback.map((line, index) => (
                  <span className="feedback-dialogue-line" key={`${line.korean}-${index}`}>
                    <b>{line.speaker}</b>
                    <span>
                      <strong lang="ko">{line.korean}</strong>
                      {line.romanization ? <em>{line.romanization}</em> : null}
                      {line.english ? <span>{line.english}</span> : null}
                    </span>
                  </span>
                ))}
              </span>
            ) : null}
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

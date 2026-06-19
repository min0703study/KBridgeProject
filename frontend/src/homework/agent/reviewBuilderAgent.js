export const EVALUATION_SKILLS = [
  'Vocabulary Understanding',
  'Vocabulary Use',
  'Grammar Ending',
  'Sentence Structure',
  'Reading Check',
  'Situation Expression',
]

export function statusForFailureCount(count) {
  if (count === 0) return 'Strong'
  if (count === 1) return 'Keep Practicing'
  return 'Needs Review'
}

export function evaluateSkills(results, questions) {
  return EVALUATION_SKILLS.map((skill) => {
    const failed = results.filter((result) => result.evaluation_skill === skill && result.answer_status !== 'correct')
    const reviewItems = failed
      .map((result) => questions.find((question) => question.question_id === result.question_id))
      .filter(Boolean)
      .map((question) => question.review_label ?? question.target_item)

    return {
      skill,
      failure_count: failed.length,
      status: statusForFailureCount(failed.length),
      review_items: [...new Set(reviewItems)],
    }
  })
}

function rotateChoices(choices, correctAnswer) {
  if (!choices?.length) return choices
  const alternatives = choices.filter((choice) => choice !== correctAnswer)
  return [correctAnswer, ...alternatives].slice(0, 4)
}

function buildVocabularyVariant(source, index) {
  if (source.question_type === 'word_meaning_choice') {
    const koreanChoice = `${source.korean} / ${source.romanization}`
    const distractors = (source.korean_distractors ?? ['학생 / haksaeng', '선생님 / seonsaengnim', '기자 / gija'])
      .filter((choice) => choice !== koreanChoice)

    return {
      ...source,
      question_id: `personalized_${source.question_id}_${index + 1}`,
      source_question_id: source.question_id,
      question_type: 'korean_word_choice',
      question: `Which Korean word means “${source.english_meaning}”?`,
      prompt: `Which Korean word means “${source.english_meaning}”?`,
      choices: [koreanChoice, ...distractors].slice(0, 4),
      correct_answer: koreanChoice,
      personalized: true,
    }
  }

  return {
    ...source,
    question_id: `personalized_${source.question_id}_${index + 1}`,
    source_question_id: source.question_id,
    question_type: 'word_meaning_choice',
    question: 'What does this Korean word mean?',
    prompt: 'What does this Korean word mean?',
    choices: rotateChoices(source.english_choices ?? source.choices, source.english_meaning),
    correct_answer: source.english_meaning,
    personalized: true,
  }
}

function buildParallelVariant(source, index) {
  const variant = source.review_variant
  if (!variant) {
    return {
      ...source,
      question_id: `personalized_${source.question_id}_${index + 1}`,
      source_question_id: source.question_id,
      choices: source.choices ? rotateChoices(source.choices, source.correct_answer) : undefined,
      personalized: true,
    }
  }

  return {
    ...source,
    ...variant,
    question_id: `personalized_${source.question_id}_${index + 1}`,
    source_question_id: source.question_id,
    evaluation_skill: source.evaluation_skill,
    personalized: true,
  }
}

export function buildPersonalizedReview({ questions, results }) {
  return results
    .filter((result) => result.answer_status !== 'correct')
    .map((result) => questions.find((question) => question.question_id === result.question_id))
    .filter(Boolean)
    .map((source, index) => (
      source.evaluation_skill === 'Vocabulary Understanding'
        ? buildVocabularyVariant(source, index)
        : buildParallelVariant(source, index)
    ))
}

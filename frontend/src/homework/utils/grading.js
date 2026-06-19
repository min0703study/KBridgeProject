function normalizeChoiceText(value) {
  return String(value ?? '')
    .trim()
    .replace(/\s*\/\s*/g, ' / ')
    .replace(/\s+/g, ' ')
    .toLowerCase()
}

function answerVariants(answer) {
  const normalized = normalizeChoiceText(answer)
  const [primary] = normalized.split(' / ')
  return new Set([normalized, primary].filter(Boolean))
}

export function normalizeAnswer(answer) {
  if (Array.isArray(answer)) {
    return answer.map((value) => normalizeChoiceText(value)).join('|')
  }

  return normalizeChoiceText(answer)
}

export function gradeQuestion(question, studentAnswer) {
  const expected = normalizeAnswer(question.correct_answer)
  const received = normalizeAnswer(studentAnswer)
  const isArrayAnswer = Array.isArray(question.correct_answer) || Array.isArray(studentAnswer)
  const isCorrect = isArrayAnswer
    ? expected === received
    : answerVariants(question.correct_answer).has(received) || answerVariants(studentAnswer).has(expected)

  return {
    is_correct: isCorrect,
    expected,
    received,
  }
}

export function formatAnswer(answer) {
  return Array.isArray(answer) ? answer.join(' ') : answer
}

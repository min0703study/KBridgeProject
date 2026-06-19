export function toStudentVisibleQuestion(question, showAnswer = false) {
  return {
    review_question_id: question.review_question_id,
    question_id: question.question_id,
    question_type: question.question_type,
    evaluation_skill: question.evaluation_skill,
    question: question.question,
    prompt: question.prompt,
    situation: question.situation,
    passage: question.passage,
    choices: question.choices,
    blocks: question.blocks,
    korean: question.korean,
    romanization: question.romanization,
    english_meaning: question.english_meaning,
    feedback_correct: question.feedback_correct,
    feedback_incorrect: question.feedback_incorrect,
    hint: question.hint,
    correct_answer: showAnswer ? question.correct_answer : undefined,
  }
}

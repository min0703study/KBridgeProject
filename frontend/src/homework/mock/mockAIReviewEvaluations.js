// Temporary demo data for the AI Review Result screen.
// Remove this file and switch HomeworkMainPage back to skillEvaluations
// when the real evaluation distribution should be displayed.
export const MOCK_AI_REVIEW_EVALUATIONS = [
  {
    skill: 'Words',
    failure_count: 0,
    status: 'Strong',
    review_items: [],
  },
  {
    skill: 'Grammar & Sentences',
    failure_count: 1,
    status: 'Keep Practicing',
    review_items: ['N입니다', '직업은 무엇입니까?'],
  },
  {
    skill: 'Reading',
    failure_count: 0,
    status: 'Strong',
    review_items: [],
  },
  {
    skill: 'Listening',
    failure_count: 1,
    status: 'Keep Practicing',
    review_items: ['직업은 무엇입니까?'],
  },
  {
    skill: 'Conversation',
    failure_count: 1,
    status: 'Keep Practicing',
    review_items: ['반갑습니다.'],
  },
]

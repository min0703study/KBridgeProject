// Temporary demo data for the AI Review Result screen.
// Remove this file and switch HomeworkMainPage back to skillEvaluations
// when the real evaluation distribution should be displayed.
export const MOCK_AI_REVIEW_EVALUATIONS = [
  {
    skill: 'Vocabulary Understanding',
    failure_count: 0,
    status: 'Strong',
    review_items: [],
  },
  {
    skill: 'Vocabulary Use',
    failure_count: 1,
    status: 'Keep Practicing',
    review_items: ['기자'],
  },
  {
    skill: 'Grammar Ending',
    failure_count: 3,
    status: 'Needs Review',
    review_items: ['N입니다', 'N입니까?', 'N이/가 아닙니다'],
  },
  {
    skill: 'Sentence Structure',
    failure_count: 0,
    status: 'Strong',
    review_items: [],
  },
  {
    skill: 'Reading Check',
    failure_count: 1,
    status: 'Keep Practicing',
    review_items: ['국적 정보 찾기'],
  },
  {
    skill: 'Situation Expression',
    failure_count: 2,
    status: 'Needs Review',
    review_items: ['안녕히 가세요.', '안녕히 계세요.'],
  },
]

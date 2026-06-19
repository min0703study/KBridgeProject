const UNIT_ID = 'unit_01'

const vocabularyQuestion = (data) => ({
  unit_id: UNIT_ID,
  evaluation_skill: 'Vocabulary Understanding',
  target_item: data.korean,
  review_label: `${data.korean} / ${data.romanization}`,
  question: data.prompt,
  prompt: data.prompt,
  error_type: 'vocabulary_understanding_error',
  ...data,
})

const choiceQuestion = (data) => ({
  unit_id: UNIT_ID,
  target_item: data.target,
  review_label: data.target,
  question: data.prompt,
  error_type: `${data.skill.toLowerCase().replaceAll(' ', '_')}_error`,
  ...data,
  evaluation_skill: data.skill,
  english_meaning: data.english,
  correct_answer: data.correct,
  review_variant: data.reviewVariant,
})

export const mockDraftQuestions = [
  vocabularyQuestion({
    question_id: 'u01_q01', question_type: 'word_meaning_choice',
    korean: '학생', romanization: 'haksaeng', english_meaning: 'student',
    prompt: 'What does this Korean word mean?',
    choices: ['student', 'teacher', 'doctor', 'reporter'], correct_answer: 'student',
    korean_distractors: ['선생님 / seonsaengnim', '의사 / uisa', '기자 / gija'],
    english_choices: ['student', 'teacher', 'doctor', 'reporter'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q02', question_type: 'word_meaning_choice',
    korean: '선생님', romanization: 'seonsaengnim', english_meaning: 'teacher',
    prompt: 'What does this Korean word mean?',
    choices: ['singer', 'soldier', 'teacher', 'cook'], correct_answer: 'teacher',
    korean_distractors: ['가수 / gasu', '군인 / gunin', '요리사 / yorisa'],
    english_choices: ['teacher', 'singer', 'soldier', 'cook'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q03', question_type: 'word_meaning_choice',
    korean: '기자', romanization: 'gija', english_meaning: 'reporter',
    prompt: 'What does this Korean word mean?',
    choices: ['company employee', 'reporter', 'doctor', 'student'], correct_answer: 'reporter',
    korean_distractors: ['회사원 / hoesawon', '의사 / uisa', '학생 / haksaeng'],
    english_choices: ['reporter', 'company employee', 'doctor', 'student'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q04', question_type: 'word_meaning_choice',
    korean: '미국 사람', romanization: 'miguk saram', english_meaning: 'American',
    prompt: 'What does this Korean word mean?',
    choices: ['Korean', 'Chinese', 'Japanese', 'American'], correct_answer: 'American',
    korean_distractors: ['한국 사람 / hanguk saram', '중국 사람 / jungguk saram', '일본 사람 / ilbon saram'],
    english_choices: ['American', 'Korean', 'Chinese', 'Japanese'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q05', question_type: 'korean_word_choice',
    korean: '의사', romanization: 'uisa', english_meaning: 'doctor',
    prompt: 'Which Korean word means “doctor”?',
    choices: ['학생 / haksaeng', '의사 / uisa', '기자 / gija', '가수 / gasu'], correct_answer: '의사 / uisa',
    english_choices: ['doctor', 'student', 'reporter', 'singer'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q06', question_type: 'korean_word_choice',
    korean: '요리사', romanization: 'yorisa', english_meaning: 'cook',
    prompt: 'Which Korean word means “cook”?',
    choices: ['요리사 / yorisa', '군인 / gunin', '회사원 / hoesawon', '선생님 / seonsaengnim'], correct_answer: '요리사 / yorisa',
    english_choices: ['cook', 'soldier', 'company employee', 'teacher'],
  }),
  vocabularyQuestion({
    question_id: 'u01_q07', question_type: 'korean_word_choice',
    korean: '영국 사람', romanization: 'yeongguk saram', english_meaning: 'British',
    prompt: 'Which Korean word means “British”?',
    choices: ['독일 사람 / dogil saram', '영국 사람 / yeongguk saram', '호주 사람 / hoju saram', '프랑스 사람 / peurangseu saram'],
    correct_answer: '영국 사람 / yeongguk saram',
    english_choices: ['British', 'German', 'Australian', 'French'],
  }),

  choiceQuestion({
    question_id: 'u01_q08', question_type: 'context_fill_choice', skill: 'Vocabulary Use', target: '기자',
    situation: 'You are introducing your job.', prompt: 'Complete the sentence.',
    korean: '저는 ___입니다.', romanization: 'jeoneun ___ imnida.', english: 'I am a ___.',
    choices: ['기자', '미국', '안녕하세요', '반가워요'], correct: '기자',
    reviewVariant: {
      target_item: '학생', review_label: '학생', situation: 'You are introducing your job.',
      korean: '저는 ___이에요.', romanization: 'jeoneun ___ ieyo.', english_meaning: 'I am a student.',
      choices: ['학생', '중국', '안녕하세요', '반가워요'], correct_answer: '학생',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q09', question_type: 'context_fill_choice', skill: 'Vocabulary Use', target: '중국',
    situation: 'You are introducing your nationality.', prompt: 'Complete the sentence.',
    korean: '저는 ___ 사람이에요.', romanization: 'jeoneun ___ saramieyo.', english: 'I am ___.',
    choices: ['학생', '중국', '선생님', '직업'], correct: '중국',
    reviewVariant: {
      target_item: '영국', review_label: '영국 사람', situation: 'You are introducing your nationality.',
      korean: '저는 ___ 사람입니다.', romanization: 'jeoneun ___ saramimnida.', english_meaning: 'I am British.',
      choices: ['기자', '영국', '학생', '직업'], correct_answer: '영국',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q10', question_type: 'context_fill_choice', skill: 'Vocabulary Use', target: '의사',
    situation: 'You are talking about Michael’s job.', prompt: 'Complete the sentence.',
    korean: '마이클 씨는 ___가 아닙니다.', romanization: 'Maikeul ssineun ___ ga animnida.', english: 'Michael is not a ___.',
    choices: ['의사', '한국', '반가워요', '안녕하세요'], correct: '의사',
    reviewVariant: {
      target_item: '기자', review_label: '기자', situation: 'You are talking about Nana’s job.',
      korean: '나나 씨는 ___가 아닙니다.', romanization: 'Nana ssineun ___ ga animnida.', english_meaning: 'Nana is not a reporter.',
      choices: ['기자', '미국', '안녕하세요', '반가워요'], correct_answer: '기자',
    },
  }),

  choiceQuestion({
    question_id: 'u01_q11', question_type: 'grammar_ending_choice', skill: 'Grammar Ending', target: 'N입니다',
    prompt: 'Complete the sentence.', korean: '저는 마이클___.', romanization: 'jeoneun Maikeul ___.', english: 'I am Michael.',
    choices: ['입니다', '입니까', '아닙니다', '안녕하세요'], correct: '입니다',
    reviewVariant: {
      target_item: 'N입니다', review_label: 'N입니다', korean: '저는 기자___.',
      romanization: 'jeoneun gija ___.', english_meaning: 'I am a reporter.',
      choices: ['입니다', '입니까', '아닙니다', '반가워요'], correct_answer: '입니다',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q12', question_type: 'grammar_ending_choice', skill: 'Grammar Ending', target: 'N입니까?',
    prompt: 'Complete the question.', korean: '마이클 씨는 미국 사람___?', romanization: 'Maikeul ssineun miguk saram ___?', english: 'Are you American, Michael?',
    choices: ['입니다', '입니까', '이에요', '아닙니다'], correct: '입니까',
    reviewVariant: {
      target_item: 'N입니까?', review_label: 'N입니까?', korean: '직업은 무엇___?',
      romanization: 'jigeobeun mueos ___?', english_meaning: 'What is your job?',
      choices: ['입니다', '입니까', '이에요', '아닙니다'], correct_answer: '입니까',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q13', question_type: 'grammar_ending_choice', skill: 'Grammar Ending', target: 'N이/가 아닙니다',
    prompt: 'Complete the sentence.', korean: '저는 학생이 ___.', romanization: 'jeoneun haksaengi ___.', english: 'I am not a student.',
    choices: ['입니다', '입니까', '아닙니다', '반갑습니다'], correct: '아닙니다',
    reviewVariant: {
      target_item: 'N이/가 아닙니다', review_label: 'N이/가 아닙니다', korean: '마이클 씨는 의사가 ___.',
      romanization: 'Maikeul ssineun uisaga ___.', english_meaning: 'Michael is not a doctor.',
      choices: ['입니다', '입니까', '아닙니다', '안녕하세요'], correct_answer: '아닙니다',
    },
  }),

  choiceQuestion({
    question_id: 'u01_q14', question_type: 'sentence_structure_choice', skill: 'Sentence Structure', target: '저는',
    prompt: 'Complete the sentence.', korean: '저___ 나나예요.', romanization: 'jeo ___ Nanayeyo.', english: 'I am Nana.',
    choices: ['는', '가', '를', '에'], correct: '는',
    reviewVariant: {
      target_item: '저는', review_label: '저는', korean: '저___ 학생이에요.',
      romanization: 'jeo ___ haksaengieyo.', english_meaning: 'I am a student.',
      choices: ['는', '가', '를', '에'], correct_answer: '는',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q15', question_type: 'sentence_structure_choice', skill: 'Sentence Structure', target: 'N이/가 아닙니다',
    prompt: 'Complete the sentence.', korean: '저는 미국 사람___ 아닙니다.', romanization: 'jeoneun miguk saram ___ animnida.', english: 'I am not American.',
    choices: ['은', '이', '가', '을'], correct: '이',
    reviewVariant: {
      target_item: 'N이/가 아닙니다', review_label: 'N이/가 아닙니다', korean: '마이클 씨는 의사___ 아닙니다.',
      romanization: 'Maikeul ssineun uisa ___ animnida.', english_meaning: 'Michael is not a doctor.',
      choices: ['는', '이', '가', '를'], correct_answer: '가',
    },
  }),
  {
    question_id: 'u01_q16', unit_id: UNIT_ID, question_type: 'sentence_order',
    evaluation_skill: 'Sentence Structure', target_item: '아니요, 저는 미국 사람이 아닙니다.',
    review_label: '아니요, 저는 미국 사람이 아닙니다.', question: 'Arrange the sentence.', prompt: 'Arrange the sentence.',
    korean: '아니요, 저는 미국 사람이 아닙니다.', romanization: 'aniyo, jeoneun miguk sarami animnida.',
    english_meaning: 'No, I am not American.', blocks: ['미국 사람이', '아닙니다', '아니요', '저는'],
    correct_answer: ['아니요', '저는', '미국 사람이', '아닙니다'], error_type: 'sentence_structure_error',
    review_variant: {
      target_item: '저는 중국 사람이에요.', review_label: '저는 중국 사람이에요.',
      korean: '저는 중국 사람이에요.', romanization: 'jeoneun jungguk saramieyo.',
      english_meaning: 'I am Chinese.', blocks: ['사람이에요', '저는', '중국'],
      correct_answer: ['저는', '중국', '사람이에요'],
    },
  },

  choiceQuestion({
    question_id: 'u01_q17', question_type: 'reading_choice', skill: 'Reading Check', target: '직업 정보 찾기',
    prompt: 'What is Michael’s job?',
    passage: [
      { korean: '안녕하세요? 저는 마이클입니다.', romanization: 'annyeonghaseyo? jeoneun Maikeurimnida.', english: 'Hello. I am Michael.' },
      { korean: '저는 영국 사람입니다.', romanization: 'jeoneun yeongguk saramimnida.', english: 'I am British.' },
      { korean: '직업은 기자입니다.', romanization: 'jigeobeun gijaimnida.', english: 'My job is reporter.' },
    ],
    korean: '직업은 기자입니다.', romanization: 'jigeobeun gijaimnida.', english: 'My job is reporter.',
    choices: ['학생', '기자', '의사', '선생님'], correct: '기자',
    reviewVariant: {
      target_item: '국적 정보 찾기', review_label: '영국 사람', prompt: 'What nationality is Michael?',
      question: 'What nationality is Michael?',
      passage: [
        { korean: '안녕하세요? 저는 마이클입니다.', romanization: 'annyeonghaseyo? jeoneun Maikeurimnida.', english: 'Hello. I am Michael.' },
        { korean: '저는 영국 사람입니다.', romanization: 'jeoneun yeongguk saramimnida.', english: 'I am British.' },
      ],
      choices: ['한국 사람', '중국 사람', '영국 사람', '미국 사람'], correct_answer: '영국 사람',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q18', question_type: 'reading_choice', skill: 'Reading Check', target: '국적 정보 찾기',
    prompt: 'What nationality is Nana?',
    passage: [
      { korean: 'A: 안녕하세요? 저는 나나예요.', romanization: 'annyeonghaseyo? jeoneun Nanayeyo.', english: 'Hello. I am Nana.' },
      { korean: 'B: 안녕하세요? 저는 마이클이에요.', romanization: 'annyeonghaseyo? jeoneun Maikeurieyo.', english: 'Hello. I am Michael.' },
      { korean: 'A: 마이클 씨는 어느 나라 사람이에요?', romanization: 'Michael ssineun eoneu nara saramieyo?', english: 'What country are you from, Michael?' },
      { korean: 'B: 저는 중국 사람이에요.', romanization: 'jeoneun jungguk saramieyo.', english: 'I am Chinese.' },
    ],
    korean: '저는 중국 사람이에요.', romanization: 'jeoneun jungguk saramieyo.', english: 'I am Chinese.',
    choices: ['한국 사람', '중국 사람', '미국 사람', '일본 사람'], correct: '중국 사람',
    reviewVariant: {
      target_item: '이름 정보 찾기', review_label: '마이클', prompt: 'What is the man’s name?',
      question: 'What is the man’s name?',
      passage: [
        { korean: '안녕하세요? 저는 마이클이에요.', romanization: 'annyeonghaseyo? jeoneun Maikeurieyo.', english: 'Hello. I am Michael.' },
        { korean: '만나서 반가워요.', romanization: 'mannaseo bangawoyo.', english: 'Nice to meet you.' },
      ],
      choices: ['나나', '마이클', '기자', '학생'], correct_answer: '마이클',
    },
  }),

  choiceQuestion({
    question_id: 'u01_q19', question_type: 'situation_expression_choice', skill: 'Situation Expression', target: '안녕하세요?',
    situation: 'You meet someone for the first time.', prompt: 'Which expression is natural?',
    korean: '안녕하세요?', romanization: 'annyeonghaseyo?', english: 'Hello.',
    choices: ['안녕하세요?', '안녕히가세요.', '직업은 무엇입니까?', '저는 학생이 아닙니다.'], correct: '안녕하세요?',
    reviewVariant: {
      target_item: '만나서 반가워요.', review_label: '만나서 반가워요.',
      situation: 'Someone introduces themselves to you for the first time.',
      choices: ['만나서 반가워요.', '안녕히 계세요.', '저는 의사가 아닙니다.', '직업은 무엇입니까?'],
      correct_answer: '만나서 반가워요.', korean: '만나서 반가워요.',
      romanization: 'mannaseo bangawoyo.', english_meaning: 'Nice to meet you.',
    },
  }),
  choiceQuestion({
    question_id: 'u01_q20', question_type: 'situation_expression_choice', skill: 'Situation Expression', target: '안녕히 계세요.',
    situation: 'You are leaving. The other person stays.', prompt: 'Which expression should you say?',
    korean: '안녕히 계세요.', romanization: 'annyeonghi gyeseyo.', english: 'Goodbye.',
    choices: ['안녕히 가세요.', '안녕히 계세요.', '반갑습니다.', '직업은 무엇입니까?'], correct: '안녕히 계세요.',
    reviewVariant: {
      target_item: '안녕히 가세요.', review_label: '안녕히 가세요.',
      situation: 'The other person is leaving. You stay.',
      choices: ['안녕히 가세요.', '안녕히 계세요.', '안녕하세요?', '저는 학생이에요.'],
      correct_answer: '안녕히 가세요.', korean: '안녕히 가세요.',
      romanization: 'annyeonghi gaseyo.', english_meaning: 'Goodbye.',
    },
  }),
]

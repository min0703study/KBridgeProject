import { useMemo, useState } from 'react';
import AppBottomNavigation from '../components/AppBottomNavigation.jsx';
import { buildPersonalizedReview, evaluateSkills } from '../homework/agent/reviewBuilderAgent.js';
import {
  MOCK_AI_REVIEW_EVALUATIONS,
  mockDraftQuestions,
  mockUnits,
} from '../homework/mock/index.js';
import { gradeQuestion } from '../homework/utils/grading.js';
import AIReviewView from '../homework/views/AIReviewView.jsx';
import MistakeReview from '../homework/views/MistakeReview.jsx';
import QuizView from '../homework/views/QuizView.jsx';
import ResultsView from '../homework/views/ResultsView.jsx';
import ReviewIntro from '../homework/views/ReviewIntro.jsx';
import UnitSelect from '../homework/views/UnitSelect.jsx';

const STUDENT_ID = 'student_demo';
const SESSION_ID = 'session_homework_001';
const USE_MOCK_AI_REVIEW = true;
const USE_DEMO_FIRST_QUESTION_PER_TYPE = true;

function firstQuestionPerType(questions) {
  const seenTypes = new Set();

  return questions.filter((question) => {
    if (seenTypes.has(question.question_type)) return false;

    seenTypes.add(question.question_type);
    return true;
  });
}

function HomeworkFlow() {
  const [screen, setScreen] = useState('units');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [checked, setChecked] = useState(false);
  const [grade, setGrade] = useState(null);
  const [results, setResults] = useState([]);
  const [activeQuestions, setActiveQuestions] = useState([]);
  const [personalizedQuestions, setPersonalizedQuestions] = useState([]);
  const [isPersonalizedSession, setIsPersonalizedSession] = useState(false);

  const selectedUnit = useMemo(() => mockUnits.find((unit) => unit.unit_id === 'unit_01'), []);
  const baseQuestions = useMemo(
    () => {
      const unitQuestions = mockDraftQuestions.filter((question) => question.unit_id === 'unit_01');

      // Temporary demo mode: keep all question data, but show only the first
      // question from each question type. Set this flag to false to restore all pages.
      return USE_DEMO_FIRST_QUESTION_PER_TYPE
        ? firstQuestionPerType(unitQuestions)
        : unitQuestions;
    },
    [],
  );
  const currentQuestion = activeQuestions[currentIndex];

  function resetQuestionState() {
    setCurrentIndex(0);
    setAnswer('');
    setChecked(false);
    setGrade(null);
    setResults([]);
  }

  function beginIntro() {
    setIsPersonalizedSession(false);
    setScreen('intro');
  }

  function startPractice() {
    resetQuestionState();
    setActiveQuestions(baseQuestions);
    setScreen('quiz');
  }

  function startPersonalizedReview() {
    if (!personalizedQuestions.length) return;
    resetQuestionState();
    setIsPersonalizedSession(true);
    setActiveQuestions(personalizedQuestions);
    setScreen('quiz');
  }

  function recordResult({ submittedAnswer, nextGrade, answerStatus }) {
    setResults((previous) => [
      ...previous,
      {
        quiz_session_id: SESSION_ID,
        student_id: STUDENT_ID,
        unit_id: currentQuestion.unit_id,
        question_id: currentQuestion.question_id,
        source_question_id: currentQuestion.source_question_id ?? currentQuestion.question_id,
        student_answer: submittedAnswer,
        is_correct: nextGrade.is_correct,
        answer_status: answerStatus,
        evaluation_skill: currentQuestion.evaluation_skill,
        error_type: nextGrade.is_correct ? null : currentQuestion.error_type,
        solving_time_sec: 12 + currentIndex,
      },
    ]);
  }

  function checkAnswer() {
    if (checked) return;
    const nextGrade = gradeQuestion(currentQuestion, answer);
    setGrade(nextGrade);
    setChecked(true);
    recordResult({
      submittedAnswer: answer,
      nextGrade,
      answerStatus: nextGrade.is_correct ? 'correct' : 'incorrect',
    });
  }

  function markDontKnow() {
    if (checked) return;
    const nextGrade = {
      is_correct: false,
      expected: currentQuestion.correct_answer,
      received: '',
      is_dont_know: true,
    };
    setAnswer('');
    setGrade(nextGrade);
    setChecked(true);
    recordResult({
      submittedAnswer: null,
      nextGrade,
      answerStatus: 'dontKnow',
    });
  }

  function nextQuestion() {
    if (currentIndex + 1 >= activeQuestions.length) {
      setScreen('mistakes');
      return;
    }
    setCurrentIndex((value) => value + 1);
    setAnswer('');
    setChecked(false);
    setGrade(null);
  }

  const reviewItems = results
    .filter((result) => result.answer_status !== 'correct')
    .map((result) => ({
      result,
      question: activeQuestions.find((question) => question.question_id === result.question_id),
    }))
    .filter((item) => item.question);

  const summary = {
    total: results.length,
    correct: results.filter((result) => result.answer_status === 'correct').length,
    incorrect: results.filter((result) => result.answer_status === 'incorrect').length,
    dontKnow: results.filter((result) => result.answer_status === 'dontKnow').length,
    needsReview: reviewItems.length,
  };

  const skillEvaluations = evaluateSkills(results, activeQuestions);

  function finishSession() {
    const nextReview = buildPersonalizedReview({ questions: activeQuestions, results });
    setPersonalizedQuestions(nextReview);
    setIsPersonalizedSession(false);
    setScreen('units');
  }

  if (screen === 'units') {
    return (
      <UnitSelect
        units={mockUnits}
        personalizedCount={personalizedQuestions.length}
        onStart={beginIntro}
        onStartPersonalized={startPersonalizedReview}
      />
    );
  }

  if (screen === 'intro') {
    return <ReviewIntro unit={selectedUnit} total={baseQuestions.length} onStart={startPractice} />;
  }

  if (screen === 'quiz') {
    return (
      <QuizView
        unit={selectedUnit}
        currentIndex={currentIndex}
        total={activeQuestions.length}
        question={currentQuestion}
        answer={answer}
        setAnswer={setAnswer}
        checked={checked}
        grade={grade}
        onCheck={checkAnswer}
        onDontKnow={markDontKnow}
        onNext={nextQuestion}
        isPersonalized={isPersonalizedSession}
      />
    );
  }

  if (screen === 'mistakes') {
    return <MistakeReview mistakes={reviewItems} onContinue={() => setScreen('results')} />;
  }

  if (screen === 'results') {
    return (
      <ResultsView
        summary={summary}
        reviewItems={reviewItems}
        evaluations={USE_MOCK_AI_REVIEW ? MOCK_AI_REVIEW_EVALUATIONS : skillEvaluations}
        onDone={finishSession}
      />
    );
  }

  return (
    <AIReviewView
      evaluations={USE_MOCK_AI_REVIEW ? MOCK_AI_REVIEW_EVALUATIONS : skillEvaluations}
      reviewItems={reviewItems}
      onDone={finishSession}
    />
  );
}

export default function HomeworkMainPage({ activeTab, onMockNavigate }) {
  return (
    <main className="app-stage">
      <div className="mobile-shell homework-shell">
        <HomeworkFlow />
        <AppBottomNavigation activeTab={activeTab} onNavigate={onMockNavigate} />
      </div>
    </main>
  );
}

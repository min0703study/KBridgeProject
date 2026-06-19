import { useMemo, useState } from 'react';
import { Gamepad2, LayoutGrid } from 'lucide-react';
import { buildPersonalizedReview, evaluateSkills } from '../homework/agent/reviewBuilderAgent.js';
import { mockDraftQuestions, mockUnits } from '../homework/mock/index.js';
import { gradeQuestion } from '../homework/utils/grading.js';
import AIReviewView from '../homework/views/AIReviewView.jsx';
import MistakeReview from '../homework/views/MistakeReview.jsx';
import QuizView from '../homework/views/QuizView.jsx';
import ResultsView from '../homework/views/ResultsView.jsx';
import ReviewIntro from '../homework/views/ReviewIntro.jsx';
import UnitSelect from '../homework/views/UnitSelect.jsx';
import { MOCK_BOTTOM_NAV_ITEMS } from '../mock/mockDashboardData.js';

const STUDENT_ID = 'student_demo';
const SESSION_ID = 'session_homework_001';

function HomeworkBottomNavigation({ onMockNavigate }) {
  return (
    <nav className="bottom-nav" aria-label="Mock app navigation">
      {MOCK_BOTTOM_NAV_ITEMS.map((item) => (
        <button
          className={`nav-item ${item.tab === 'homework' ? 'is-active' : ''}`}
          type="button"
          key={item.id}
          onClick={() => {
            if (
              item.tab === 'dashboard' ||
              item.tab === 'game' ||
              item.tab === 'homework' ||
              item.tab === 'chatbot'
            ) {
              onMockNavigate(item.tab);
            }
          }}
        >
          {item.iconSrc ? (
            <img src={item.iconSrc} alt={item.iconAlt} />
          ) : item.lucide === 'game' ? (
            <Gamepad2 size={30} strokeWidth={1.9} aria-hidden="true" />
          ) : (
            <LayoutGrid size={30} strokeWidth={1.9} aria-hidden="true" />
          )}
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
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
    () => mockDraftQuestions.filter((question) => question.unit_id === 'unit_01'),
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
    return <ResultsView summary={summary} reviewItems={reviewItems} onContinue={() => setScreen('ai-review')} />;
  }

  return (
    <AIReviewView
      evaluations={skillEvaluations}
      reviewItems={reviewItems}
      onDone={finishSession}
    />
  );
}

export default function HomeworkMainPage({ onMockNavigate }) {
  return (
    <main className="app-stage">
      <div className="mobile-shell homework-shell">
        <HomeworkFlow />
        <HomeworkBottomNavigation onMockNavigate={onMockNavigate} />
      </div>
    </main>
  );
}

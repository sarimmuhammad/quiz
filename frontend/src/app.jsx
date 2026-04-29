import React, { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:5000';

function App() {
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedTopic, setSelectedTopic] = useState('');
  const [expandedTopic, setExpandedTopic] = useState('');
  const [selectedSubtopics, setSelectedSubtopics] = useState([]);
  const [questionType, setQuestionType] = useState('mcq');
  const [difficulty, setDifficulty] = useState('Medium');
  const [numQuestions, setNumQuestions] = useState(5);
  const [quiz, setQuiz] = useState(null);
  const [quizResult, setQuizResult] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stage, setStage] = useState('setup');

  useEffect(() => {
    fetchSubjects();
  }, []);

  const fetchSubjects = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/subjects`);
      const data = await response.json();
      setSubjects(data.subjects);
    } catch (err) {
      setError('Failed to load subjects');
    }
  };

  const fetchTopics = async (subject) => {
    try {
      const response = await fetch(`${API_BASE_URL}/topics/${encodeURIComponent(subject)}`);
      const data = await response.json();
      setTopics(data.topics);
    } catch (err) {
      setError('Failed to load topics');
    }
  };

  const handleSubjectChange = (e) => {
    const subject = e.target.value;
    setSelectedSubject(subject);
    setSelectedTopic('');
    setSelectedSubtopics([]);
    setExpandedTopic('');
    setTopics([]);
    if (subject) {
      fetchTopics(subject);
    }
  };

  const toggleSubtopic = (subtopic) => {
    setSelectedSubtopics((prev) =>
      prev.includes(subtopic) ? prev.filter((s) => s !== subtopic) : [...prev, subtopic]
    );
  };

  const handleTopicClick = (topicName) => {
    setSelectedTopic(topicName);
    setSelectedSubtopics([]);
    setExpandedTopic(expandedTopic === topicName ? '' : topicName);
  };

  const generateQuiz = async () => {
    if (!selectedSubject || !selectedTopic) {
      setError('Please select subject and topic');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/generate-quiz`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subject: selectedSubject,
          topic: selectedTopic,
          selected_subtopics: selectedSubtopics,
          question_type: questionType,
          difficulty: difficulty,
          num_questions: numQuestions,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate quiz');
      }

      const data = await response.json();
      setQuiz(data);
      setQuizResult(null);
      setUserAnswers({});
      setSubmitted(false);
      setStage('quiz');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId, answer) => {
    setUserAnswers({
      ...userAnswers,
      [questionId]: answer,
    });
  };

  const submitQuiz = async () => {
    setLoading(true);
    setError('');

    try {
      const answers = Object.entries(userAnswers).map(([id, answer]) => ({
        id: Number(id),
        answer,
      }));

      const response = await fetch(`${API_BASE_URL}/submit-quiz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quiz_id:    quiz.quiz_id,
          subject:    quiz.subject,
          topic:      quiz.topic,
          subtopics:  quiz.subtopics,
          difficulty: quiz.difficulty,
          questions:  quiz.questions,
          answers,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to submit quiz');
      }

      const data = await response.json();
      setQuizResult(data);
      setSubmitted(true);
      setStage('results');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetQuiz = () => {
    setQuiz(null);
    setQuizResult(null);
    setUserAnswers({});
    setSubmitted(false);
    setStage('setup');
    setError('');
    setSelectedSubtopics([]);
    setExpandedTopic('');
  };

  const renderQuestion = (question) => {
    const userAns    = userAnswers[question.id];
    const isCorrect  = quizResult
      ? quizResult.results.find((r) => r.id === question.id)?.is_correct
      : false;

    return (
      <div key={question.id} className="question-card">
        <div className="question-header">
          <span className="question-number">Question {question.id}</span>
          <span className={`question-type-badge ${question.type}`}>
            {question.type.replace('_', ' ')}
          </span>
        </div>

        <div className="question-text">{question.question}</div>

        {question.code_snippet && (
          <div className="code-block">
            <pre>
              <code>{question.code_snippet}</code>
            </pre>
          </div>
        )}

        {question.case_study && (
          <div className="case-study">
            <h4>Case Study:</h4>
            <p>{question.case_study}</p>
          </div>
        )}

        {question.type === 'mcq' && question.options && (
          <div className="options-container">
            {question.options.map((option) => {
              const isSelected    = userAns === option.key;
              const showCorrect   = submitted && option.key === question.correct_answer;
              const showIncorrect = submitted && isSelected && !isCorrect;

              return (
                <button
                  key={option.key}
                  className={`option-btn ${isSelected ? 'selected' : ''} ${
                    showCorrect ? 'correct' : ''
                  } ${showIncorrect ? 'incorrect' : ''}`}
                  onClick={() => !submitted && handleAnswerChange(question.id, option.key)}
                  disabled={submitted}
                >
                  <span className="option-key">{option.key}</span>
                  <span className="option-text">{option.text}</span>
                </button>
              );
            })}
          </div>
        )}

        {question.type !== 'mcq' && (
          <div className="answer-input-container">
            <textarea
              className="answer-textarea"
              placeholder="Type your answer here..."
              value={userAns || ''}
              onChange={(e) => handleAnswerChange(question.id, e.target.value)}
              disabled={submitted}
              rows="4"
            />
            {submitted && (
              <div className="correct-answer-display">
                <strong>Correct Answer:</strong>
                <p>{question.correct_answer}</p>
              </div>
            )}
          </div>
        )}

        {submitted && question.type === 'mcq' && (
          <div className="answer-feedback">
            {isCorrect ? (
              <span className="feedback-correct">✓ Correct</span>
            ) : (
              <span className="feedback-incorrect">✗ Incorrect</span>
            )}
          </div>
        )}
      </div>
    );
  };

  // ─── SETUP STAGE ───────────────────────────────────────────────
  if (stage === 'setup') {
    return (
      <div className="app-container">
        <div className="header">
          <h1 className="app-title">AI Quiz Generator</h1>
          <p className="app-subtitle">Intelligent University-Level Assessment Platform</p>
        </div>

        <div className="setup-container">
          <div className="setup-card">
            <h2>Configure Your Quiz</h2>

            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label>Subject</label>
              <select value={selectedSubject} onChange={handleSubjectChange} className="select-input">
                <option value="">Select Subject</option>
                {subjects.map((subject) => (
                  <option key={subject} value={subject}>
                    {subject}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Topic & Subtopics</label>
              {!selectedSubject ? (
                <div className="select-input" style={{ color: '#aaa', cursor: 'not-allowed' }}>
                  Select a subject first
                </div>
              ) : (
                <div className="topic-list">
                  {topics.map((topic) => (
                    <div key={topic.main_topic} className="topic-item">
                      <button
                        className={`topic-row ${selectedTopic === topic.main_topic ? 'active' : ''}`}
                        onClick={() => handleTopicClick(topic.main_topic)}
                        type="button"
                      >
                        <span>{topic.main_topic}</span>
                        <span className="topic-arrow">
                          {expandedTopic === topic.main_topic ? '▲' : '▼'}
                        </span>
                      </button>
                      {expandedTopic === topic.main_topic && (
                        <div className="subtopic-list">
                          <button
                            className="subtopic-select-all"
                            type="button"
                            onClick={() =>
                              setSelectedSubtopics(
                                selectedSubtopics.length === topic.subtopics.length
                                  ? []
                                  : [...topic.subtopics]
                              )
                            }
                          >
                            {selectedSubtopics.length === topic.subtopics.length
                              ? 'Deselect All'
                              : 'Select All'}
                          </button>
                          {topic.subtopics.map((sub) => (
                            <label key={sub} className="subtopic-item">
                              <input
                                type="checkbox"
                                checked={selectedSubtopics.includes(sub)}
                                onChange={() => toggleSubtopic(sub)}
                              />
                              <span>{sub}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {selectedTopic && (
                <div className="selected-info">
                  ✓ {selectedTopic}
                  {selectedSubtopics.length > 0
                    ? ` — ${selectedSubtopics.length} subtopic(s) selected`
                    : ' — all subtopics'}
                </div>
              )}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Question Type</label>
                <select
                  value={questionType}
                  onChange={(e) => setQuestionType(e.target.value)}
                  className="select-input"
                >
                  <option value="mcq">Multiple Choice</option>
                  <option value="definition">Definition</option>
                  <option value="short_answer">Short Answer</option>
                  <option value="scenario_based">Scenario Based</option>
                  <option value="code_based">Code Based</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>

              <div className="form-group">
                <label>Difficulty</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="select-input"
                >
                  <option value="Easy">Easy</option>
                  <option value="Medium">Medium</option>
                  <option value="Hard">Hard</option>
                </select>
              </div>

              <div className="form-group">
                <label>Number of Questions</label>
                <select
                  value={numQuestions}
                  onChange={(e) => setNumQuestions(Number(e.target.value))}
                  className="select-input"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={15}>15</option>
                </select>
              </div>
            </div>

            <button
              className="generate-btn"
              onClick={generateQuiz}
              disabled={loading || !selectedSubject || !selectedTopic}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Generating Quiz...
                </>
              ) : (
                'Generate Quiz'
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── QUIZ STAGE ────────────────────────────────────────────────
  if (stage === 'quiz') {
    return (
      <div className="app-container">
        <div className="quiz-header">
          <div>
            <h2 className="quiz-title">{quiz.subject}</h2>
            <p className="quiz-subtitle">{quiz.topic}</p>
          </div>
          <div className="quiz-meta">
            <span className="meta-badge">{quiz.difficulty}</span>
            <span className="meta-badge">{quiz.question_type.replace('_', ' ')}</span>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="quiz-container">
          {quiz.questions.map((question) => renderQuestion(question))}
        </div>

        <div className="submit-container">
          <button
            className="submit-btn"
            onClick={submitQuiz}
            disabled={submitted || loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Submitting...
              </>
            ) : submitted ? (
              'Quiz Submitted'
            ) : (
              'Submit Quiz'
            )}
          </button>
        </div>
      </div>
    );
  }

  // ─── RESULTS STAGE ─────────────────────────────────────────────
  if (stage === 'results') {
    const score      = quizResult?.score      ?? 0;
    const total      = quizResult?.total      ?? quiz.questions.length;
    const percentage = quizResult?.percentage ?? 0;

    return (
      <div className="app-container">
        <div className="results-container">
          <div className="results-card">
            <h2 className="results-title">Quiz Results</h2>
            <div className="score-display">
              <div className="score-circle">
                <div className="score-number">{score}</div>
                <div className="score-total">/ {total}</div>
              </div>
              <div className="percentage">{percentage}%</div>
            </div>
            <div className="results-details">
              <div className="detail-item">
                <span className="detail-label">Subject:</span>
                <span className="detail-value">{quiz.subject}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Topic:</span>
                <span className="detail-value">{quiz.topic}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Difficulty:</span>
                <span className="detail-value">{quiz.difficulty}</span>
              </div>
            </div>
            <div className="results-actions">
              <button className="review-btn" onClick={() => setStage('quiz')}>
                Review Answers
              </button>
              <button className="new-quiz-btn" onClick={resetQuiz}>
                New Quiz
              </button>
            </div>
          </div>
        </div>

        <div className="quiz-container">
          {quiz.questions.map((question) => renderQuestion(question))}
        </div>
      </div>
    );
  }

  return null;
}

export default App;
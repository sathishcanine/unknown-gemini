/* ==========================================================================
   APP CONTROLLER & LOGIC: TNPSC PREP
   ========================================================================== */

// App State
const state = {
  activeScreen: 'screen-home',
  activeGroup: 'Group 1',
  activeTopic: null,
  questions: [], // Loaded from questions_db.json
  testHistory: [], // Loaded from LocalStorage
  currentTest: null, // Info of the ongoing test
  textbookMapping: {
    "Nature of Indian Economy": {
      title: "Nature of Indian Economy",
      titleTa: "இந்திய பொருளாதாரத்தின் இயல்பு",
      book: "Class 11 Economics Textbook (11ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 7: Indian Economy (அத்தியாயம் 7: இந்திய பொருளாதாரம்)",
      pages: "Pages 141 - 156",
      focus: "Focus on features of Indian economy (strength & weaknesses), mixed economy concept, and development indicators (GNH, HDI, standard of living)."
    },
    "Planning Commission": {
      title: "Planning Commission & Five Year Plans",
      titleTa: "திட்டக்குழு மற்றும் ஐந்தாண்டு திட்டங்கள்",
      book: "Class 11 Economics Textbook (11ஆம் வகுப்பு பொருளியல்)",
      chapter: "Chapter 8: Economic Planning (அத்தியாயம் 8: பொருளாதார திட்டமிடல்)",
      pages: "Pages 160 - 172",
      focus: "Focus on the history of planning commission, planning models (Gandhian, Nehruvian), and objectives/performance of Five Year Plans."
    }
  }
};

// DOM Elements
const DOM = {
  themeToggle: document.getElementById('theme-toggle'),
  statusTime: document.getElementById('status-time'),
  headerGroupDisplay: document.getElementById('header-group-display'),
  screenContainer: document.getElementById('screen-container'),
  
  // Navigation Tabs
  tabs: {
    home: document.getElementById('tab-home'),
    syllabus: document.getElementById('tab-syllabus'),
    advisor: document.getElementById('tab-advisor')
  },
  
  // Screens
  screens: {
    home: document.getElementById('screen-home'),
    syllabus: document.getElementById('screen-syllabus'),
    topicDetail: document.getElementById('screen-topic-detail'),
    quiz: document.getElementById('screen-quiz'),
    results: document.getElementById('screen-results'),
    advisor: document.getElementById('screen-advisor')
  },
  
  // Home Screen Elements
  groupBtns: document.querySelectorAll('.segment-btn'),
  weaknessBanner: document.getElementById('weakness-banner'),
  weaknessBannerText: document.getElementById('weakness-banner-text'),
  weaknessBannerAction: document.getElementById('weakness-banner-action'),
  masteryPercent: document.getElementById('mastery-percent'),
  masteryProgressFill: document.getElementById('mastery-progress-fill'),
  statsTotalTests: document.getElementById('stats-total-tests'),
  statsCorrectRatio: document.getElementById('stats-correct-ratio'),
  statsAvgAccuracy: document.getElementById('stats-avg-accuracy'),
  subjectCardEconomics: document.getElementById('subject-card-economics'),
  subjectEconProgressPct: document.getElementById('subject-econ-progress-pct'),
  subjectEconProgressFill: document.getElementById('subject-econ-progress-fill'),
  subjectEconQuestionsCount: document.getElementById('subject-econ-questions-count'),
  
  // Syllabus Screen Elements
  topicsContainer: document.getElementById('topics-container'),
  btnToHome: document.querySelectorAll('.btn-to-home'),
  
  // Topic Detail Screen Elements
  topicDetailTitle: document.getElementById('topic-detail-title'),
  topicDetailPyqCount: document.getElementById('topic-detail-pyq-count'),
  topicDetailBatchesContainer: document.getElementById('topic-detail-batches-container'),
  btnBackToSyllabus: document.getElementById('btn-back-to-syllabus'),
  btnStartPyq: document.getElementById('btn-start-pyq'),
  
  // Quiz Screen Elements
  quizTopicDisplay: document.getElementById('quiz-topic-display'),
  quizTimerDisplay: document.getElementById('quiz-timer-display'),
  quizProgressText: document.getElementById('quiz-progress-text'),
  quizProgressBarFill: document.getElementById('quiz-progress-bar-fill'),
  quizQuestionEn: document.getElementById('quiz-question-en'),
  quizQuestionTa: document.getElementById('quiz-question-ta'),
  quizOptionsContainer: document.getElementById('quiz-options-container'),
  quizPrevBtn: document.getElementById('quiz-prev-btn'),
  quizNextBtn: document.getElementById('quiz-next-btn'),
  quizQuitBtn: document.getElementById('quiz-quit-btn'),
  
  // Results Screen Elements
  resultsTopicDisplay: document.getElementById('results-topic-display'),
  resultsScoreValue: document.getElementById('results-score-value'),
  resultsAccuracyPct: document.getElementById('results-accuracy-pct'),
  resultsFeedbackMessage: document.getElementById('results-feedback-message'),
  resultsCorrectCount: document.getElementById('results-correct-count'),
  resultsWrongCount: document.getElementById('results-wrong-count'),
  resultsTimeTaken: document.getElementById('results-time-taken'),
  resultsReviewContainer: document.getElementById('results-review-container'),
  resultsBtnToAdvisor: document.getElementById('results-btn-to-advisor'),
  resultsDasharray: document.getElementById('results-dasharray'),
  
  // Advisor Screen Elements
  advisorSummaryText: document.getElementById('advisor-summary-text'),
  weaknessReviewCta: document.getElementById('weakness-review-cta'),
  weaknessReviewDescription: document.getElementById('weakness-review-description'),
  advisorLaunchReviewBtn: document.getElementById('advisor-launch-review-btn'),
  advisorRecommendationsList: document.getElementById('advisor-recommendations-list')
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTheme();
  loadData();
  setupEventListeners();
});

// Real-time status bar clock
function initClock() {
  const updateClock = () => {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    hours = hours < 10 ? '0' + hours : hours;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    DOM.statusTime.textContent = `${hours}:${minutes}`;
  };
  updateClock();
  setInterval(updateClock, 30000);
}

// Light/Dark Theme toggle logic
function initTheme() {
  const savedTheme = localStorage.getItem('tnpsc_theme') || 'dark';
  if (savedTheme === 'light') {
    document.body.classList.remove('dark-theme');
    document.body.classList.add('light-theme');
  } else {
    document.body.classList.add('dark-theme');
    document.body.classList.remove('light-theme');
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Theme Toggle click
  DOM.themeToggle.addEventListener('click', () => {
    const isDark = document.body.classList.toggle('dark-theme');
    document.body.classList.toggle('light-theme', !isDark);
    localStorage.setItem('tnpsc_theme', isDark ? 'dark' : 'light');
  });

  // Group selection (Group 1, 2, 4)
  DOM.groupBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      DOM.groupBtns.forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      
      state.activeGroup = e.target.getAttribute('data-group');
      DOM.headerGroupDisplay.textContent = `${state.activeGroup} Prep`;
      
      // Update UI matching new group filter
      updateDashboardStats();
      renderSyllabusTopics();
    });
  });

  // Navigation tab bar clicks
  Object.keys(DOM.tabs).forEach(tabKey => {
    DOM.tabs[tabKey].addEventListener('click', (e) => {
      // Find button closest to clicked target
      const btn = e.target.closest('.nav-tab');
      if (!btn) return;
      
      const targetScreenId = btn.getAttribute('data-screen');
      navigateTo(targetScreenId);
    });
  });

  // Back to dashboard buttons
  DOM.btnToHome.forEach(btn => {
    btn.addEventListener('click', () => {
      navigateTo('screen-home');
    });
  });

  // Subject Economics Card click -> navigates to syllabus view
  DOM.subjectCardEconomics.addEventListener('click', () => {
    navigateTo('screen-syllabus');
  });

  // Topic Detail Navigation Event Listeners
  DOM.btnBackToSyllabus.addEventListener('click', () => {
    navigateTo('screen-syllabus');
  });

  DOM.btnStartPyq.addEventListener('click', () => {
    if (state.activeTopic) {
      startQuiz(state.activeTopic, "pyq");
    }
  });

  // Quiz Navigation Button Clicks
  DOM.quizPrevBtn.addEventListener('click', () => navigateQuizQuestion(-1));
  DOM.quizNextBtn.addEventListener('click', () => navigateQuizQuestion(1));
  DOM.quizQuitBtn.addEventListener('click', quitQuiz);

  // Results to Advisor button
  DOM.resultsBtnToAdvisor.addEventListener('click', () => {
    navigateTo('screen-advisor');
  });

  // Weakness Review launch from Advisor
  DOM.advisorLaunchReviewBtn.addEventListener('click', () => {
    startWeaknessReviewQuiz();
  });

  // Weakness Banner review launch
  DOM.weaknessBannerAction.addEventListener('click', () => {
    navigateTo('screen-advisor');
    // Scroll to recommendations list
    DOM.advisorRecommendationsList.scrollIntoView({ behavior: 'smooth' });
  });
}

// Navigate between screens
function navigateTo(screenId) {
  // Save current active screen
  state.activeScreen = screenId;
  
  // Update Tab Bar Active States
  Object.keys(DOM.tabs).forEach(tabKey => {
    const tab = DOM.tabs[tabKey];
    const target = tab.getAttribute('data-screen');
    tab.classList.toggle('active', target === screenId);
  });

  // Update Screens Active CSS class
  Object.keys(DOM.screens).forEach(screenKey => {
    const screen = DOM.screens[screenKey];
    if (screen.id === screenId) {
      screen.classList.add('active');
    } else {
      screen.classList.remove('active');
    }
  });

  // Custom UI triggers on navigation
  if (screenId === 'screen-home') {
    updateDashboardStats();
  } else if (screenId === 'screen-syllabus') {
    renderSyllabusTopics();
  } else if (screenId === 'screen-topic-detail') {
    renderTopicDetailScreen();
  } else if (screenId === 'screen-advisor') {
    updateAdvisorScreen();
  }
}

// Load Data from local JSON and LocalStorage
async function loadData() {
  try {
    // 1. Fetch questions_db.json with cache-buster
    const response = await fetch('questions_db.json?v=' + Date.now());
    if (!response.ok) throw new Error('Failed to load questions database');
    state.questions = await response.json();
    
    // 2. Load History from LocalStorage
    const storedHistory = localStorage.getItem('tnpsc_test_history');
    if (storedHistory) {
      state.testHistory = JSON.parse(storedHistory);
    }
    
    // 3. Update UI
    DOM.subjectEconQuestionsCount.textContent = `${state.questions.length} Questions Available`;
    updateDashboardStats();
    
  } catch (err) {
    console.error('Error loading data: ', err);
    // Fallback Mock Questions in case of local network issue
    state.questions = getFallbackQuestions();
    state.testHistory = [];
    DOM.subjectEconQuestionsCount.textContent = `${state.questions.length} Questions Available`;
    updateDashboardStats();
  }
}

// ==========================================================================
// STATS & METRICS ENGINE
// ==========================================================================
function updateDashboardStats() {
  const history = state.testHistory;
  
  // Filter questions by active subject ("Economy") and active Group
  const subjectQuestions = getFilteredQuestions("Economy");
  
  // Calc totals
  const totalTests = history.length;
  DOM.statsTotalTests.textContent = totalTests;
  
  if (totalTests === 0) {
    DOM.statsCorrectRatio.textContent = "0/0";
    DOM.statsAvgAccuracy.textContent = "0%";
    DOM.masteryPercent.textContent = "0%";
    DOM.masteryProgressFill.style.width = "0%";
    
    DOM.subjectEconProgressPct.textContent = "0%";
    DOM.subjectEconProgressFill.style.width = "0%";
    DOM.weaknessBanner.classList.add('d-none');
    return;
  }
  
  let totalCorrect = 0;
  let totalSolved = 0;
  let accuracySum = 0;
  
  history.forEach(session => {
    totalCorrect += session.correctCount;
    totalSolved += session.totalCount;
    accuracySum += (session.correctCount / session.totalCount);
  });
  
  DOM.statsCorrectRatio.textContent = `${totalCorrect}/${totalSolved}`;
  const avgAccuracy = Math.round((totalCorrect / totalSolved) * 100);
  DOM.statsAvgAccuracy.textContent = `${avgAccuracy}%`;
  
  // Subject progress calculation
  // Progress pct represents: (Number of distinct questions solved with correct answer / Total available questions)
  const correctlySolvedIds = new Set();
  history.forEach(session => {
    Object.keys(session.answers).forEach(qIndexStr => {
      const qIndex = parseInt(qIndexStr);
      const question = session.questions[qIndex];
      const selected = session.answers[qIndex];
      if (question && selected === question.correct_option) {
        // Unique ID based on question text hash
        correctlySolvedIds.add(question.question_en);
      }
    });
  });
  
  const totalAvailableCount = subjectQuestions.length;
  DOM.subjectEconQuestionsCount.textContent = `${totalAvailableCount} Questions Available`;
  
  const solvedCount = Array.from(correctlySolvedIds).filter(qText => 
    subjectQuestions.some(q => q.question_en === qText)
  ).length;
  
  const progressPct = totalAvailableCount > 0 ? Math.round((solvedCount / totalAvailableCount) * 100) : 0;
  
  DOM.subjectEconProgressPct.textContent = `${progressPct}%`;
  DOM.subjectEconProgressFill.style.width = `${progressPct}%`;
  
  // Overall mastery is linked to average accuracy for now
  DOM.masteryPercent.textContent = `${avgAccuracy}%`;
  DOM.masteryProgressFill.style.width = `${avgAccuracy}%`;
  
  // Check for critical weakness to display dashboard alert banner
  const weakness = getTopicWeaknessReport();
  const critical = weakness.find(w => w.status === 'critical');
  
  if (critical) {
    DOM.weaknessBanner.classList.remove('d-none');
    const textbook = state.textbookMapping[critical.topic];
    DOM.weaknessBannerText.textContent = `Weakness detected in "${critical.topic}" (${critical.accuracy}% accuracy). Review the ${textbook ? textbook.book : 'school textbooks'}.`;
  } else {
    DOM.weaknessBanner.classList.add('d-none');
  }
}

// Get average scores of tested topics
function getTopicWeaknessReport() {
  const history = state.testHistory;
  if (history.length === 0) return [];
  
  // Group results by topic
  const topicStats = {};
  history.forEach(session => {
    if (!topicStats[session.topic]) {
      topicStats[session.topic] = { correct: 0, total: 0 };
    }
    topicStats[session.topic].correct += session.correctCount;
    topicStats[session.topic].total += session.totalCount;
  });
  
  return Object.keys(topicStats).map(topicName => {
    const stats = topicStats[topicName];
    const pct = Math.round((stats.correct / stats.total) * 100);
    
    let status = 'good';
    if (pct < 70) {
      status = 'critical';
    } else if (pct < 85) {
      status = 'warning';
    }
    
    return {
      topic: topicName,
      accuracy: pct,
      status: status
    };
  });
}

// Filter questions by active Group, type (pyq vs practice), and batch
function getFilteredQuestions(subject = "Economy", topic = null, type = null, batch = null) {
  return state.questions.filter(q => {
    // Subject filter
    const matchesSubject = q.subject.toLowerCase() === subject.toLowerCase();
    
    // Topic filter
    const matchesTopic = topic ? q.topic === topic : true;
    
    // Type filter
    const matchesType = type ? q.type === type : true;
    
    // Batch filter
    const matchesBatch = batch ? q.batch === batch : true;
    
    // Group exam filter: 
    // TNPSC Syllabus details overlaps, so we display:
    // 1. Group-specific exams (e.g. Group 4 matches G4)
    // 2. "Other Exams" (Gazetted/Technical exam crops) to guarantee sufficient question volume for the POC
    // 3. Practice questions are generated from textbooks and apply to all groups
    let matchesGroup = false;
    if (q.type === 'practice') {
      matchesGroup = true;
    } else {
      if (state.activeGroup === 'Group 1') {
        matchesGroup = q.group === 'Group 1' || q.group === 'Other Exams';
      } else if (state.activeGroup === 'Group 2') {
        matchesGroup = q.group === 'Group 2' || q.group === 'Other Exams';
      } else if (state.activeGroup === 'Group 4') {
        matchesGroup = q.group === 'Group 4' || q.group === 'Other Exams';
      }
    }
    
    return matchesSubject && matchesTopic && matchesGroup && matchesType && matchesBatch;
  });
}

// ==========================================================================
// SYLLABUS & TOPICS VIEW
// ==========================================================================
function renderSyllabusTopics() {
  DOM.topicsContainer.innerHTML = '';
  
  // Discover distinct topics in questions
  const topics = Array.from(new Set(state.questions.map(q => q.topic)));
  
  topics.forEach(topicName => {
    const filteredQs = getFilteredQuestions("Economy", topicName);
    if (filteredQs.length === 0) return; // Skip if no questions match this group
    
    // Get past records for this topic
    const topicTests = state.testHistory.filter(h => h.topic === topicName && h.group === state.activeGroup);
    
    let badgeText = 'Not Started';
    let badgeClass = 'blue';
    
    if (topicTests.length > 0) {
      let totalCorrect = 0;
      let totalSolved = 0;
      topicTests.forEach(t => {
        totalCorrect += t.correctCount;
        totalSolved += t.totalCount;
      });
      const accuracy = Math.round((totalCorrect / totalSolved) * 100);
      
      badgeText = `${accuracy}% Correct`;
      if (accuracy < 70) {
        badgeClass = 'red';
      } else if (accuracy < 85) {
        badgeClass = 'blue';
      } else {
        badgeClass = 'green';
      }
    }
    
    const card = document.createElement('div');
    card.className = 'topic-card';
    card.innerHTML = `
      <div class="topic-info-side">
        <h4>${topicName}</h4>
        <div class="topic-stats-row">
          <span class="topic-badge ${badgeClass}">${badgeText}</span>
          <span class="topic-q-count">${filteredQs.length} Questions</span>
        </div>
      </div>
      <button class="topic-start-btn" data-topic="${topicName}">▶</button>
    `;
    
    DOM.topicsContainer.appendChild(card);
  });
  
  // Attach start button event listeners
  DOM.topicsContainer.querySelectorAll('.topic-start-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const topic = e.target.getAttribute('data-topic');
      state.activeTopic = topic;
      navigateTo('screen-topic-detail');
    });
  });
}

// Render Topic Detail Screen
function renderTopicDetailScreen() {
  const topic = state.activeTopic;
  if (!topic) return;
  
  DOM.topicDetailTitle.textContent = topic;
  
  // 1. Get PYQ count
  const pyqs = getFilteredQuestions("Economy", topic, "pyq");
  DOM.topicDetailPyqCount.textContent = `${pyqs.length} PYQs Available`;
  DOM.btnStartPyq.disabled = pyqs.length === 0;
  
  // 2. Render Practice Batches
  DOM.topicDetailBatchesContainer.innerHTML = '';
  
  // Get all unique practice batches in state.questions for this topic
  const batches = Array.from(new Set(
    state.questions
      .filter(q => q.topic === topic && q.type === 'practice')
      .map(q => q.batch)
  )).filter(Boolean);
  
  if (batches.length === 0) {
    DOM.topicDetailBatchesContainer.innerHTML = `<p class="text-muted" style="font-size: 13px; text-align: center; margin-top: 10px;">No practice batches generated yet for this topic.</p>`;
    return;
  }
  
  batches.sort().forEach(batchName => {
    const batchQs = getFilteredQuestions("Economy", topic, "practice", batchName);
    
    // Check if this batch has been completed
    const batchTests = state.testHistory.filter(h => h.topic === topic && h.group === 'Practice' && h.questions[0] && h.questions[0].batch === batchName);
    
    let badgeText = 'Not Started';
    let badgeClass = 'blue';
    
    if (batchTests.length > 0) {
      let totalCorrect = 0;
      let totalSolved = 0;
      batchTests.forEach(t => {
        totalCorrect += t.correctCount;
        totalSolved += t.totalCount;
      });
      const accuracy = Math.round((totalCorrect / totalSolved) * 100);
      badgeText = `${accuracy}% Score`;
      badgeClass = accuracy < 70 ? 'red' : (accuracy < 85 ? 'blue' : 'green');
    }
    
    const batchCard = document.createElement('div');
    batchCard.className = 'topic-card';
    batchCard.style.padding = '12px 16px';
    batchCard.innerHTML = `
      <div class="topic-info-side">
        <h4 style="font-family: var(--font-header); font-size: 14px; font-weight: 600;">${batchName}</h4>
        <div class="topic-stats-row">
          <span class="topic-badge ${badgeClass}">${badgeText}</span>
          <span class="topic-q-count">${batchQs.length} Questions</span>
        </div>
      </div>
      <button class="topic-start-btn batch-start-btn" data-batch="${batchName}" style="background: var(--accent-gradient); box-shadow: var(--shadow-glow); border: none; padding: 6px 12px; border-radius: var(--radius-sm); color: #fff; font-size: 12px; font-weight: 700; width: auto; height: auto;">Start</button>
    `;
    
    batchCard.querySelector('.batch-start-btn').addEventListener('click', () => {
      startQuiz(topic, "practice", batchName);
    });
    
    DOM.topicDetailBatchesContainer.appendChild(batchCard);
  });
}

// ==========================================================================
// QUIZ ENGINE
// ==========================================================================
function startQuiz(topic, type = null, batch = null) {
  // Get matching questions
  const availableQs = getFilteredQuestions("Economy", topic, type, batch);
  if (availableQs.length === 0) {
    alert("No questions available for this topic and parameters.");
    return;
  }
  
  // For practice batches, take all available questions. For PYQs, take up to 10.
  const countToPick = type === 'practice' ? availableQs.length : Math.min(10, availableQs.length);
  
  const shuffled = [...availableQs].sort(() => 0.5 - Math.random());
  const selectedQs = shuffled.slice(0, countToPick);
  
  // Initialize quiz state
  state.currentTest = {
    topic: topic,
    type: type,
    batch: batch,
    questions: selectedQs,
    currentIndex: 0,
    answers: {},
    startTime: Date.now(),
    timeLeft: selectedQs.length * 60, // 60s per question
    timer: null
  };
  
  // Update UI Elements
  DOM.quizTopicDisplay.textContent = type === 'practice' ? `${topic} (${batch})` : `${topic} (PYQs)`;
  updateQuizQuestion();
  navigateTo('screen-quiz');
  
  // Start Timer
  startQuizTimer();
}

function startQuizTimer() {
  if (state.currentTest.timer) clearInterval(state.currentTest.timer);
  
  const updateTimerDisplay = () => {
    const test = state.currentTest;
    const mins = Math.floor(test.timeLeft / 60);
    const secs = test.timeLeft % 60;
    DOM.quizTimerDisplay.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    
    if (test.timeLeft <= 0) {
      clearInterval(test.timer);
      alert("Time is up! Submitting your answers.");
      submitQuiz();
    }
    test.timeLeft--;
  };
  
  updateTimerDisplay();
  state.currentTest.timer = setInterval(updateTimerDisplay, 1000);
}

function updateQuizQuestion() {
  const test = state.currentTest;
  const index = test.currentIndex;
  const question = test.questions[index];
  
  // Update progress
  DOM.quizProgressText.textContent = `Question ${index + 1} of ${test.questions.length}`;
  const pct = Math.round(((index + 1) / test.questions.length) * 100);
  DOM.quizProgressBarFill.style.width = `${pct}%`;
  
  // Question text
  DOM.quizQuestionEn.innerHTML = question.question_en.replace(/\n/g, '<br>');
  DOM.quizQuestionTa.innerHTML = question.question_ta ? question.question_ta.replace(/\n/g, '<br>') : "தமிழ் வினா விடுபட்டுள்ளது.";
  
  // Options
  DOM.quizOptionsContainer.innerHTML = '';
  question.options.forEach(opt => {
    // If Tamil option is missing or null, provide fallbacks (specifically for Answer Not Known options)
    let optTextTa = opt.text_ta;
    if (opt.key === 'E' && !optTextTa) {
      optTextTa = "விடை தெரியவில்லை"; // standard TNPSC E option
    }
    if (optTextTa === opt.text_en) {
      optTextTa = "";
    }
    
    const optionDiv = document.createElement('div');
    optionDiv.className = `option-item ${test.answers[index] === opt.key ? 'selected' : ''}`;
    optionDiv.setAttribute('data-key', opt.key);
    optionDiv.innerHTML = `
      <div class="option-key">${opt.key}</div>
      <div class="option-text-wrapper">
        <div class="option-text-en">${opt.text_en}</div>
        ${optTextTa ? `<div class="option-text-ta">${optTextTa}</div>` : ''}
      </div>
    `;
    
    optionDiv.addEventListener('click', () => selectOption(opt.key));
    DOM.quizOptionsContainer.appendChild(optionDiv);
  });
  
  // Nav buttons states
  DOM.quizPrevBtn.disabled = index === 0;
  
  if (index === test.questions.length - 1) {
    DOM.quizNextBtn.textContent = 'Submit';
    DOM.quizNextBtn.classList.add('submit-type');
  } else {
    DOM.quizNextBtn.textContent = 'Next';
    DOM.quizNextBtn.classList.remove('submit-type');
  }
}

function selectOption(key) {
  const test = state.currentTest;
  test.answers[test.currentIndex] = key;
  
  // Redraw option selection highlight
  const optionItems = DOM.quizOptionsContainer.querySelectorAll('.option-item');
  optionItems.forEach(item => {
    if (item.getAttribute('data-key') === key) {
      item.classList.add('selected');
    } else {
      item.classList.remove('selected');
    }
  });
}

function navigateQuizQuestion(direction) {
  const test = state.currentTest;
  
  // If next click on last question -> trigger Submit
  if (direction === 1 && test.currentIndex === test.questions.length - 1) {
    submitQuiz();
    return;
  }
  
  test.currentIndex += direction;
  updateQuizQuestion();
}

function quitQuiz() {
  if (confirm("Are you sure you want to quit this test? Your progress will be lost.")) {
    const test = state.currentTest;
    clearInterval(test.timer);
    state.currentTest = null;
    if (state.activeTopic) {
      navigateTo('screen-topic-detail');
    } else {
      navigateTo('screen-syllabus');
    }
  }
}

function submitQuiz() {
  const test = state.currentTest;
  clearInterval(test.timer);
  
  // Calc score details
  let correctCount = 0;
  test.questions.forEach((q, idx) => {
    if (test.answers[idx] === q.correct_option) {
      correctCount++;
    }
  });
  
  const totalCount = test.questions.length;
  const timeTaken = Math.round((Date.now() - test.startTime) / 1000);
  
  // Session object
  const session = {
    id: 'test_' + Date.now(),
    topic: test.topic,
    group: test.type === 'practice' ? 'Practice' : state.activeGroup,
    questions: test.questions,
    answers: test.answers,
    correctCount: correctCount,
    totalCount: totalCount,
    timeTaken: timeTaken,
    timestamp: new Date().toLocaleDateString()
  };
  
  // Save to state history
  state.testHistory.unshift(session); // Add to beginning
  localStorage.setItem('tnpsc_test_history', JSON.stringify(state.testHistory));
  
  // Clear quiz state
  state.currentTest = null;
  
  // Render results view
  displayResults(session);
}

// ==========================================================================
// RESULTS VIEW & RENDERERS
// ==========================================================================
function displayResults(session) {
  DOM.resultsTopicDisplay.textContent = session.topic;
  DOM.resultsScoreValue.textContent = `${session.correctCount}/${session.totalCount}`;
  
  const accuracy = Math.round((session.correctCount / session.totalCount) * 100);
  DOM.resultsAccuracyPct.textContent = `${accuracy}% Accuracy`;
  
  // Animate Circular Progress score ring
  // Stroke Dasharray total length = 263.8
  const offset = 263.8 * (1 - (session.correctCount / session.totalCount));
  DOM.resultsDasharray.style.strokeDashoffset = offset;
  
  // Feedbacks
  let feedback = "Review your textbook references below to improve.";
  if (accuracy === 100) feedback = "Outstanding! Perfect score. You've mastered this topic!";
  else if (accuracy >= 80) feedback = "Excellent job! You have solid command over this area.";
  else if (accuracy >= 60) feedback = "Good effort, but review the recommended pages to boost score.";
  DOM.resultsFeedbackMessage.textContent = feedback;
  
  DOM.resultsCorrectCount.textContent = session.correctCount;
  DOM.resultsWrongCount.textContent = session.totalCount - session.correctCount;
  
  // Format duration
  const mins = Math.floor(session.timeTaken / 60);
  const secs = session.timeTaken % 60;
  DOM.resultsTimeTaken.textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  
  // Review answers list
  DOM.resultsReviewContainer.innerHTML = '';
  session.questions.forEach((q, idx) => {
    const userSelected = session.answers[idx];
    const isCorrect = userSelected === q.correct_option;
    
    const card = document.createElement('div');
    card.className = `review-card ${isCorrect ? 'correct' : 'wrong'}`;
    
    // Header
    card.innerHTML = `
      <div class="review-question-text">
        <strong>Q${idx+1}.</strong> ${q.question_en}<br>
        <span class="text-muted" style="font-size:12px;">${q.question_ta || ''}</span>
      </div>
      <div class="review-choices"></div>
    `;
    
    const choicesList = card.querySelector('.review-choices');
    q.options.forEach(opt => {
      let optTextTa = opt.text_ta;
      if (opt.key === 'E' && !optTextTa) optTextTa = "விடை தெரியவில்லை";
      if (optTextTa === opt.text_en) optTextTa = "";
      
      const isThisCorrect = opt.key === q.correct_option;
      const isThisUserSelection = opt.key === userSelected;
      
      let modifierClass = '';
      let badgeHtml = '';
      
      if (isThisCorrect) {
        modifierClass = 'correct';
        badgeHtml = `<span class="review-choice-badge correct">Correct</span>`;
      } else if (isThisUserSelection && !isCorrect) {
        modifierClass = 'user-wrong';
        badgeHtml = `<span class="review-choice-badge wrong">Your Pick</span>`;
      }
      
      const choiceDiv = document.createElement('div');
      choiceDiv.className = `review-choice-item ${modifierClass}`;
      choiceDiv.innerHTML = `
        <span class="review-choice-key">${opt.key}.</span>
        <div style="display:flex; flex-direction:column;">
          <span>${opt.text_en}</span>
          ${optTextTa ? `<span class="text-muted" style="font-size:11px;">${optTextTa}</span>` : ''}
        </div>
        ${badgeHtml}
      `;
      choicesList.appendChild(choiceDiv);
    });
    
    // Add Textbook reference matching the question's topic
    const textbook = state.textbookMapping[q.topic];
    if (textbook) {
      const expDiv = document.createElement('div');
      expDiv.className = 'review-explanation';
      expDiv.innerHTML = `
        📖 <strong>Study Guide Reference:</strong><br>
        ${textbook.book} &bull; ${textbook.chapter}<br>
        <span style="color:var(--primary-glow); font-weight:600;">Recommended Reading: ${textbook.pages}</span>
      `;
      card.appendChild(expDiv);
    }
    
    DOM.resultsReviewContainer.appendChild(card);
  });
  
  navigateTo('screen-results');
}

// ==========================================================================
// AI STUDY ADVISOR & RECOMMENDATION SYSTEM
// ==========================================================================
function updateAdvisorScreen() {
  DOM.advisorRecommendationsList.innerHTML = '';
  
  const report = getTopicWeaknessReport();
  
  if (state.testHistory.length === 0) {
    DOM.advisorSummaryText.textContent = "Take topic-wise quizzes in the 'Syllabus' tab. The Advisor will analyze your scores and build a tailored study guide highlighting weak spots.";
    DOM.weaknessReviewCta.classList.add('d-none');
    
    // Render blank or initial study topics list as placeholder
    Object.keys(state.textbookMapping).forEach(topicKey => {
      renderAdvisorCard({ topic: topicKey, accuracy: null, status: 'none' });
    });
    return;
  }
  
  // Set overview message
  const criticalList = report.filter(r => r.status === 'critical');
  const warningList = report.filter(r => r.status === 'warning');
  
  if (criticalList.length > 0) {
    DOM.advisorSummaryText.textContent = `Alert: We detected weaknesses in ${criticalList.length} topic(s). Follow the textbook guides below to improve.`;
  } else if (warningList.length > 0) {
    DOM.advisorSummaryText.textContent = `You're doing well! Just a few areas in Economics require fine-tuning.`;
  } else {
    DOM.advisorSummaryText.textContent = `Outstanding work! You've achieved mastery (85%+ accuracy) across all tested Economics topics!`;
  }
  
  // Weakness Review CTA logic
  // Gather incorrect questions from test history
  const incorrectQuestions = getIncorrectQuestions();
  if (incorrectQuestions.length > 0) {
    DOM.weaknessReviewCta.classList.remove('d-none');
    DOM.weaknessReviewDescription.textContent = `You have ${incorrectQuestions.length} questions previously answered incorrectly. Boost mastery by repeating them!`;
    DOM.advisorLaunchReviewBtn.textContent = `Start Review (${incorrectQuestions.length} Qs)`;
  } else {
    DOM.weaknessReviewCta.classList.add('d-none');
  }
  
  // Render recommendations matching syllabus topics
  const topicsInApp = Array.from(new Set(state.questions.map(q => q.topic)));
  
  topicsInApp.forEach(topicName => {
    const stats = report.find(r => r.topic === topicName);
    if (stats) {
      renderAdvisorCard(stats);
    } else {
      renderAdvisorCard({ topic: topicName, accuracy: null, status: 'none' });
    }
  });
}

function renderAdvisorCard(stats) {
  const textbook = state.textbookMapping[stats.topic];
  if (!textbook) return; // Skip if no mapping exists for this topic
  
  const card = document.createElement('div');
  
  let borderClass = 'good';
  let badgeText = 'Mastery achieved';
  let badgeClass = 'good';
  let advice = "Your accuracy is high. Keep practicing and revise before exams.";
  
  if (stats.status === 'critical') {
    borderClass = 'critical';
    badgeText = `${stats.accuracy}% Accuracy`;
    badgeClass = 'critical';
    advice = `<strong>Critical Action Required:</strong> Your score is low. Allocate study time to read the following textbook pages. Pay close attention to: ${textbook.focus}`;
  } else if (stats.status === 'warning') {
    borderClass = 'warning';
    badgeText = `${stats.accuracy}% Accuracy`;
    badgeClass = 'warning';
    advice = `<strong>Focus Required:</strong> You are very close to mastery. Review these textbook concepts to eliminate simple mistakes: ${textbook.focus}`;
  } else if (stats.status === 'none') {
    borderClass = 'none';
    badgeText = 'Not Tested';
    badgeClass = 'warning';
    advice = "No score data yet. Complete a quiz to analyze your performance.";
  }
  
  card.className = `advisor-card ${borderClass}`;
  card.innerHTML = `
    <div class="advisor-card-header">
      <span class="advisor-card-title">${textbook.titleTa}<br><small style="color:var(--text-muted);">${stats.topic}</small></span>
      <span class="advisor-card-badge ${badgeClass}">${badgeText}</span>
    </div>
    <div class="advisor-card-body">
      <p>${advice}</p>
    </div>
    ${stats.status !== 'none' ? `
      <div class="advisor-card-recommendation">
        <span class="book-icon">📚</span>
        <div class="book-details">
          <span class="book-title">${textbook.book}</span>
          <span class="book-chapters">${textbook.chapter}</span>
          <span style="color:var(--primary-glow); font-weight:700; font-size:11px; margin-top:2px;">Recommended study: ${textbook.pages}</span>
        </div>
      </div>
    ` : ''}
    <button class="advisor-card-action-btn" data-topic="${stats.topic}">Practice This Topic</button>
  `;
  
  card.querySelector('.advisor-card-action-btn').addEventListener('click', () => {
    startQuiz(stats.topic);
  });
  
  DOM.advisorRecommendationsList.appendChild(card);
}

// Gather unique questions got wrong in past history
function getIncorrectQuestions() {
  const incorrectMap = new Map();
  const correctSet = new Set();
  
  // Go through history chronological (oldest to newest) to see what is currently incorrect
  // Reverse history list for chronological sweep
  const chronoHistory = [...state.testHistory].reverse();
  
  chronoHistory.forEach(session => {
    Object.keys(session.answers).forEach(qIndexStr => {
      const qIndex = parseInt(qIndexStr);
      const question = session.questions[qIndex];
      const selected = session.answers[qIndex];
      
      if (question) {
        const qKey = question.question_en;
        if (selected === question.correct_option) {
          correctSet.add(qKey);
          incorrectMap.delete(qKey); // If got correct later, remove from wrong list
        } else {
          if (!correctSet.has(qKey)) {
            incorrectMap.set(qKey, question); // Add to wrong list
          }
        }
      }
    });
  });
  
  return Array.from(incorrectMap.values());
}

function startWeaknessReviewQuiz() {
  const incorrectQs = getIncorrectQuestions();
  if (incorrectQs.length === 0) return;
  
  // Shuffle and take top 10
  const shuffled = incorrectQs.sort(() => 0.5 - Math.random());
  const selectedQs = shuffled.slice(0, Math.min(10, shuffled.length));
  
  state.currentTest = {
    topic: "Weakness Review",
    questions: selectedQs,
    currentIndex: 0,
    answers: {},
    startTime: Date.now(),
    timeLeft: selectedQs.length * 60,
    timer: null
  };
  
  DOM.quizTopicDisplay.textContent = "Weakness Review";
  updateQuizQuestion();
  navigateTo('screen-quiz');
  
  startQuizTimer();
}

// Fallback Mock Questions to run offline if network fails to fetch JSON
function getFallbackQuestions() {
  return [
    {
      "question_en": "Mixed Economy implies",
      "question_ta": "கலப்பு பொருளாதாரம் --------------- குறிக்கிறது.",
      "options": [
        { "key": "A", "text_en": "Co-existence of Small and Large industries", "text_ta": "சிறு மற்றும் பேரளவுத் தொழில்கள் இணைந்து செயல்படுதல்" },
        { "key": "B", "text_en": "Co-existence of Public and Private sectors", "text_ta": "பொது மற்றும் தனியார் துறைகள் இணைந்து செயல்படுதல்" },
        { "key": "C", "text_en": "Co-existence of Labour intensive and Capital intensive technology", "text_ta": "உழைப்பு தொழில்நுட்ப செறிவு மற்றும் மூலதன தொழில்நுட்ப செறிவு இணைந்து செயல்படுதல்" },
        { "key": "D", "text_en": "Co-existence of National and Foreign companies", "text_ta": "தேசிய மற்றும் அயல்நாட்டு நிறுவனங்கள் இணைந்து செயல்படுதல்" }
      ],
      "correct_option": "B",
      "subject": "Economy",
      "topic": "Nature of Indian Economy",
      "source_exam": "Mock Exam",
      "group": "Other Exams"
    }
  ];
}

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../models/question.dart';
import '../models/history.dart';
import '../services/api_service.dart';

class AppState extends ChangeNotifier {
  final ApiService _apiService = ApiService();

  // Navigation State
  String _activeScreen = 'home';
  String get activeScreen => _activeScreen;

  /// Where system/UI back should return from results (`topic_detail` | `performance` | `home`).
  String _resultsReturnScreen = 'home';

  // Auth State
  // Starts unknown; never show Login vs Home until prefs restore finishes.
  bool _authReady = false;
  bool get authReady => _authReady;

  bool _isAuthenticated = false;
  bool get isAuthenticated => _isAuthenticated;

  String? _activeSubject;
  String? get activeSubject => _activeSubject;

  String _activeGroup = 'Group 1';
  String get activeGroup => _activeGroup;

  String _userEmail = 'test_user';
  String get userEmail => _userEmail;

  String? _activeTopic;
  String? get activeTopic => _activeTopic;

  bool _isDarkMode = true;
  bool get isDarkMode => _isDarkMode;

  // Content language for menus/titles from API (en | ta)
  String _contentLanguage = 'en';
  String get contentLanguage => _contentLanguage;
  bool get isTamilContent => _contentLanguage == 'ta';

  // Subjects / Syllabus loaded from backend
  List<Map<String, dynamic>> _subjects = [];
  List<Map<String, dynamic>> get subjects => _subjects;

  List<Map<String, dynamic>> _syllabusList = [];
  List<Map<String, dynamic>> get syllabusList => _syllabusList;

  /// Tamil & English hub: null | `languages` | `units`
  String? _tamilHubLevel;
  String? get tamilHubLevel => _tamilHubLevel;

  /// Selected General Tamil unit id from API (e.g. `Kalaichorkal`).
  String? _tamilUnitId;
  String? get tamilUnitId => _tamilUnitId;

  /// Server-driven Podhu Tamil units (`GET /api/tamil/units`).
  List<Map<String, dynamic>> _tamilUnits = [];
  List<Map<String, dynamic>> get tamilUnits => _tamilUnits;

  Map<String, dynamic>? get selectedTamilUnit {
    if (_tamilUnitId == null) return null;
    for (final u in _tamilUnits) {
      if ((u['id'] ?? '').toString() == _tamilUnitId) return u;
    }
    return null;
  }

  /// Syllabus rows visible for the current Tamil unit (or full list otherwise).
  List<Map<String, dynamic>> get visibleSyllabusList {
    if (_activeSubject != 'Tamil' || _tamilUnitId == null) {
      return _syllabusList;
    }
    final unit = selectedTamilUnit;
    if (unit == null) return _syllabusList;
    final raw = unit['topics'];
    final names = <String>{
      if (raw is List) ...raw.map((e) => e.toString()),
    };
    if (names.isEmpty) return _syllabusList;
    return _syllabusList
        .where((t) => names.contains((t['name'] ?? '').toString()))
        .toList();
  }

  String tamilUnitDisplayName(String? unitId) {
    if (unitId == null || unitId.isEmpty) return '';
    for (final u in _tamilUnits) {
      if ((u['id'] ?? '').toString() == unitId) {
        return (u['name_ta'] ?? u['name_en'] ?? unitId).toString();
      }
    }
    return unitId;
  }

  String tamilUnitSubtitle(Map<String, dynamic> unit) {
    final ta = (unit['subtitle_ta'] ?? '').toString().trim();
    if (ta.isNotEmpty) return ta;
    final en = (unit['subtitle_en'] ?? '').toString().trim();
    if (en.isNotEmpty) return en;
    final tc = unit['topic_count'];
    final qc = unit['questions_count'];
    if (tc != null || qc != null) {
      return '${tc ?? 0} topics · ${qc ?? 0} Q';
    }
    return '';
  }

  bool _loading = false;
  bool get loading => _loading;

  // History & Stats State
  List<HistoryEntry> _testHistory = [];
  List<HistoryEntry> get testHistory => _testHistory;

  int _totalTests = 0;
  int get totalTests => _totalTests;

  int _totalCorrect = 0;
  int get totalCorrect => _totalCorrect;

  int _totalSolved = 0;
  int get totalSolved => _totalSolved;

  int _avgAccuracy = 0;
  int get avgAccuracy => _avgAccuracy;

  int _masteryPercent = 0;
  int get masteryPercent => _masteryPercent;

  Map<String, dynamic>? _weaknessReport;
  Map<String, dynamic>? get weaknessReport => _weaknessReport;

  // Active Quiz State
  bool _quizInProgress = false;
  bool get quizInProgress => _quizInProgress;

  List<Question> _quizQuestions = [];
  List<Question> get quizQuestions => _quizQuestions;

  int _currentQuestionIndex = 0;
  int get currentQuestionIndex => _currentQuestionIndex;

  Map<int, String> _selectedAnswers = {}; // questionIndex -> optionKey
  Map<int, String> get selectedAnswers => _selectedAnswers;

  bool _isTimed = false;
  bool get isTimed => _isTimed;

  int _remainingSeconds = 1800; // 30 minutes default
  int get remainingSeconds => _remainingSeconds;

  int _timeTakenSeconds = 0;
  int get timeTakenSeconds => _timeTakenSeconds;

  Timer? _quizTimer;
  HistoryEntry? _lastCompletedSession;
  HistoryEntry? get lastCompletedSession => _lastCompletedSession;

  // Per-question timing instrumentation (used for admin analytics)
  final Map<int, DateTime> _questionFirstViewedAt = {};
  final Map<int, int> _questionResponseTimeMs = {};

  AppState() {
    _init();
  }

  Future<void> _init() async {
    _loading = true;

    // Restore session first so the UI never flashes Login for signed-in users.
    await loadLocalPreferences();
    _authReady = true;
    notifyListeners();

    // Web does not support serverClientId; skip Google init there (guest login used instead).
    // Android/iOS: use the Web client ID from the same Firebase project as google-services.json
    // (project 636736405953 / firestoredemo-c4c59). Do not use a different GCP project's IDs.
    if (!kIsWeb) {
      try {
        await GoogleSignIn.instance.initialize(
          serverClientId:
              '636736405953-2nvcd7iqao7uapsvmducd5ra6itck7q3.apps.googleusercontent.com',
        );
      } catch (e) {
        print("Google Sign-In Init Error: $e");
      }
    }

    await fetchSubjects();
    await syncStatsWithBackend();

    _loading = false;
    notifyListeners();

    // Fire-and-forget analytics; never blocks app startup.
    unawaited(_logAppOpenAndSyncDevice());
  }

  Future<void> _logAppOpenAndSyncDevice() async {
    try {
      // Only log app_open for DAU/engagement. Device metadata (platform /
      // OS / app version / IP country) is intentionally not collected.
      if (_isAuthenticated && _userEmail != 'test_user') {
        await _apiService.logEvent(_userEmail, 'app_open');
      }
    } catch (e) {
      debugPrint('Analytics init failed silently: $e');
    }
  }

  // Load preferences from local storage
  Future<void> loadLocalPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    _activeGroup = prefs.getString('active_group') ?? 'Group 1';
    _isAuthenticated = prefs.getBool('is_authenticated') ?? false;
    _userEmail = prefs.getString('user_email') ?? 'test_user';
    _contentLanguage = prefs.getString('content_language') ?? 'en';

    final historyJson = prefs.getString('test_history');
    if (historyJson != null) {
      try {
        List decoded = jsonDecode(historyJson);
        _testHistory = decoded.map((h) => HistoryEntry.fromJson(h)).toList();
      } catch (e) {
        print("Error parsing local test history: $e");
        _testHistory = [];
      }
    }
  }

  // Save preferences to local storage
  Future<void> saveLocalPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('active_group', _activeGroup);
    await prefs.setBool('is_authenticated', _isAuthenticated);
    await prefs.setString('user_email', _userEmail);
    await prefs.setString('content_language', _contentLanguage);

    final historyJson = jsonEncode(_testHistory.map((h) => h.toJson()).toList());
    await prefs.setString('test_history', historyJson);
  }

  Future<void> toggleTheme() async {
    _isDarkMode = !_isDarkMode;
    await saveLocalPreferences();
    notifyListeners();
  }

  Future<void> setContentLanguage(String language) async {
    final next = language == 'ta' ? 'ta' : 'en';
    if (_contentLanguage == next) return;
    _contentLanguage = next;
    await saveLocalPreferences();
    notifyListeners();
  }

  Future<void> toggleContentLanguage() async {
    await setContentLanguage(isTamilContent ? 'en' : 'ta');
  }

  /// Subject title from API: `name` (EN) or `name_ta` (TA). Falls back to EN if TA empty.
  String subjectDisplayName(String? subjectId) {
    Map<String, dynamic>? match;
    for (final sub in _subjects) {
      if (sub['id'] == subjectId) {
        match = sub;
        break;
      }
    }
    if (match == null) {
      return subjectId ?? '';
    }
    if (isTamilContent) {
      final ta = (match['name_ta'] ?? '').toString().trim();
      if (ta.isNotEmpty) return ta;
    }
    return (match['name'] ?? subjectId ?? '').toString();
  }

  /// Topic title from syllabus item: EN `name` or API `textbook.titleTa`.
  String topicDisplayNameFromItem(Map<String, dynamic> item) {
    final en = (item['name'] ?? '').toString();
    if (!isTamilContent) return en;
    final tb = item['textbook'];
    if (tb is Map) {
      final ta = (tb['titleTa'] ?? '').toString().trim();
      if (ta.isNotEmpty) return ta;
    }
    return en;
  }

  String activeTopicDisplayName() {
    if (_activeTopic == null) return subjectDisplayName(_activeSubject);
    for (final item in _syllabusList) {
      if (item['name'] == _activeTopic) {
        return topicDisplayNameFromItem(item);
      }
    }
    return _activeTopic!;
  }

  /// Hub chrome labels (not subject/topic titles from API).
  String hubLabel(String english) {
    if (!isTamilContent) return english;
    const ta = {
      'General Studies': 'பொது அறிவு',
      'Tamil & English': 'தமிழ் மற்றும் ஆங்கிலம்',
      'Past Year Questions': 'முந்தைய ஆண்டு வினாக்கள்',
      'Questions Available': 'வினாக்கள் உள்ளன',
      'Preparation Hub': 'தயாரிப்பு மையம்',
      'Syllabus': 'பாடத்திட்டம்',
      'Practice Batch': 'பயிற்சித் தொகுதி',
      'Practice Batches': 'பயிற்சித் தொகுதிகள்',
      'Completed': 'முடிந்தவை',
      'Start': 'தொடங்கு',
      'Retake': 'மீண்டும் எழுது',
      'Current Affairs Batches': 'நடப்பு நிகழ்வுகள் தொகுதிகள்',
      'Current Affairs': 'நடப்பு நிகழ்வுகள்',
      'TVK-Government Policies': 'த.வெ.க அரசு கொள்கைகள்',
      'Very Important': 'மிக முக்கியம்',
      'Central Government Schemes': 'மத்திய அரசுத் திட்டங்கள்',
      'Union Schemes': 'மத்திய அரசுத் திட்டங்கள்',
      'Tamil': 'தமிழ்',
      'General Tamil': 'பொதுத் தமிழ்',
      'General English': 'பொது ஆங்கிலம்',
      'Coming soon': 'விரைவில்',
      'Grammar': 'இலக்கணம்',
      'Vocabulary': 'சொல்லகராதி',
    };
    return ta[english] ?? english;
  }

  String questionsAvailableLabel(Object? count) {
    return '$count ${hubLabel('Questions Available')}';
  }

  /// Display label for a batch key like "Batch 1" / "1" / "Batch 2".
  String practiceBatchLabel(String batchKey) {
    final match = RegExp(r'(\d+)').firstMatch(batchKey);
    final num = match?.group(1) ?? batchKey;
    return '${hubLabel('Practice Batch')} $num';
  }

  /// Normalize batch keys so "Batch 1" and "1" match.
  String normalizeBatchKey(String? batchKey) {
    if (batchKey == null || batchKey.trim().isEmpty) return '';
    final match = RegExp(r'(\d+)').firstMatch(batchKey);
    return match?.group(1) ?? batchKey.trim().toLowerCase();
  }

  String _sessionBatchKey(HistoryEntry entry) {
    if (entry.batch.trim().isNotEmpty) {
      return normalizeBatchKey(entry.batch);
    }
    for (final q in entry.questions) {
      if (q.type.toLowerCase() != 'pyq' && q.batch.trim().isNotEmpty) {
        return normalizeBatchKey(q.batch);
      }
    }
    return '';
  }

  /// Locally known completed practice batches for a topic (device history).
  Set<String> localCompletedBatchKeys(String topicName) {
    final keys = <String>{};
    for (final h in _testHistory) {
      if (h.topic != topicName) continue;
      final hasPractice = h.questions.any((q) => q.type.toLowerCase() != 'pyq');
      if (!hasPractice && h.batch.trim().isEmpty) continue;
      final key = _sessionBatchKey(h);
      if (key.isNotEmpty) keys.add(key);
    }
    return keys;
  }

  HistoryEntry? latestLocalBatchSession(String topicName, String batchKey) {
    final target = normalizeBatchKey(batchKey);
    HistoryEntry? latest;
    for (final h in _testHistory) {
      if (h.topic != topicName) continue;
      if (_sessionBatchKey(h) != target) continue;
      if (latest == null || h.timestamp > latest.timestamp) {
        latest = h;
      }
    }
    return latest;
  }

  Future<void> setGroup(String group) async {
    _activeGroup = group;
    await saveLocalPreferences();
    await syncStatsWithBackend();
    notifyListeners();
  }

  Future<void> fetchSubjects() async {
    try {
      _subjects = await _apiService.getSubjects();
    } catch (e) {
      print("Error fetching subjects: $e");
    }
  }

  Future<void> selectSubject(String subjectId) async {
    // Leaving Tamil hub when opening any other subject path.
    if (subjectId != 'Tamil') {
      _tamilHubLevel = null;
      _tamilUnitId = null;
    }
    _activeSubject = subjectId;
    _activeTopic = null;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      _syllabusList = await _apiService.getSyllabus(subjectId);
    } catch (e) {
      print("Error fetching syllabus for $subjectId: $e");
      _syllabusList = [];
    }

    _loading = false;
    notifyListeners();
  }

  void openTamilEnglishHub() {
    _tamilHubLevel = 'languages';
    _tamilUnitId = null;
    _activeSubject = null;
    _activeTopic = null;
    _activeScreen = 'home';
    notifyListeners();
  }

  Future<void> openGeneralTamilUnits() async {
    _tamilHubLevel = 'units';
    _tamilUnitId = null;
    _activeSubject = null;
    _activeTopic = null;
    _activeScreen = 'home';
    _loading = true;
    notifyListeners();
    try {
      _tamilUnits = await _apiService.getTamilUnits();
    } catch (e) {
      print("Error fetching Tamil units: $e");
      _tamilUnits = [];
    }
    _loading = false;
    notifyListeners();
  }

  /// Back within Tamil & English hub (languages ↔ units ↔ home root).
  /// Returns true if a hub level was popped.
  bool backTamilHub() {
    if (_tamilHubLevel == 'units') {
      _tamilHubLevel = 'languages';
      _tamilUnitId = null;
      notifyListeners();
      return true;
    }
    if (_tamilHubLevel == 'languages') {
      _tamilHubLevel = null;
      _tamilUnitId = null;
      notifyListeners();
      return true;
    }
    return false;
  }

  Future<void> selectTamilUnit(String unitId) async {
    _tamilUnitId = unitId;
    _tamilHubLevel = 'units';
    _activeSubject = 'Tamil';
    _activeTopic = null;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      // Prefer server-side unit filter; fall back to full syllabus + client filter.
      _syllabusList = await _apiService.getSyllabus('Tamil', unit: unitId);
      if (_syllabusList.isEmpty) {
        _syllabusList = await _apiService.getSyllabus('Tamil');
      }
    } catch (e) {
      print("Error fetching Tamil syllabus for unit $unitId: $e");
      _syllabusList = [];
    }

    _loading = false;
    notifyListeners();
  }

  /// Back from syllabus: Tamil units → unit picker; else home root.
  void navigateBackFromSyllabus() {
    if (_activeSubject == 'Tamil' && _tamilUnitId != null) {
      _tamilUnitId = null;
      _tamilHubLevel = 'units';
      _activeSubject = null;
      _activeTopic = null;
      _syllabusList = [];
      _activeScreen = 'home';
      notifyListeners();
      return;
    }
    navigateToHome();
  }

  void selectTopic(String topicName) {
    _activeTopic = topicName;
    _activeScreen = 'topic_detail';
    notifyListeners();
  }

  Future<void> selectCurrentAffairsTopic(String topicName) async {
    _activeSubject = 'Current Affairs';
    _activeTopic = topicName;
    _activeScreen = 'topic_detail';
    _loading = true;
    notifyListeners();
    try {
      _syllabusList = await _apiService.getSyllabus('Current Affairs');
    } catch (e) {
      print("Error preloading Current Affairs syllabus: $e");
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void navigateToHome() {
    _activeScreen = 'home';
    _activeSubject = null;
    _activeTopic = null;
    _tamilHubLevel = null;
    _tamilUnitId = null;
    notifyListeners();
  }

  void navigateToSyllabus() {
    if (_activeSubject != null) {
      _activeScreen = 'syllabus';
    } else if (_tamilHubLevel != null) {
      _activeScreen = 'home';
    } else {
      _activeScreen = 'home';
    }
    notifyListeners();
  }

  void navigateToPerformance() {
    _activeScreen = 'performance';
    _activeSubject = null;
    _activeTopic = null;
    notifyListeners();
  }

  void navigateToAdvisor() {
    _activeScreen = 'advisor';
    notifyListeners();
  }

  void navigateToProfile() {
    _activeScreen = 'profile';
    _activeSubject = null;
    _activeTopic = null;
    notifyListeners();
  }

  void navigateToResults() {
    _resultsReturnScreen = _activeTopic != null ? 'topic_detail' : 'home';
    _activeScreen = 'results';
    notifyListeners();
  }

  /// Open a past session in Test Results (from Performance history).
  Future<void> openSessionResults(int sessionId) async {
    final detail = await _apiService.getSessionDetail(
      userId: _userEmail,
      sessionId: sessionId,
    );

    final questions = (detail['questions'] as List? ?? [])
        .map((q) => Question.fromJson(Map<String, dynamic>.from(q as Map)))
        .toList();
    final rawAnswers = detail['answers'] as Map? ?? {};
    final answers = rawAnswers.map(
      (k, v) => MapEntry(k.toString(), v.toString()),
    );

    _lastCompletedSession = HistoryEntry(
      topic: (detail['topic_name'] ?? '').toString(),
      group: _activeGroup,
      correctCount: detail['correct_count'] ?? 0,
      totalCount: detail['total_count'] ?? questions.length,
      answers: answers,
      questions: questions,
      timestamp: (detail['timestamp_ms'] as num?)?.toDouble() ??
          DateTime.now().millisecondsSinceEpoch.toDouble(),
      batch: (detail['batch'] ?? '').toString(),
    );
    _timeTakenSeconds = detail['time_taken'] ?? 0;
    _resultsReturnScreen = 'performance';
    _activeScreen = 'results';
    notifyListeners();
  }

  /// Handle Android/iOS system back / swipe-back.
  /// Returns `true` if navigation was handled in-app (app must NOT exit).
  /// Returns `false` only on Home root — caller may allow the OS to exit.
  /// For `quiz`, returns `true` but does not navigate; caller should show quit UI.
  bool handleSystemBack() {
    switch (_activeScreen) {
      case 'home':
        return backTamilHub();
      case 'quiz':
        return true;
      case 'topic_detail':
        navigateToSyllabus();
        return true;
      case 'syllabus':
        navigateBackFromSyllabus();
        return true;
      case 'results':
        if (_resultsReturnScreen == 'performance') {
          navigateToPerformance();
        } else if (_activeTopic != null) {
          _activeScreen = 'topic_detail';
          notifyListeners();
        } else {
          navigateToHome();
        }
        return true;
      case 'profile':
        navigateToHome();
        return true;
      case 'performance':
      case 'advisor':
        navigateToHome();
        return true;
      default:
        navigateToHome();
        return true;
    }
  }

  // Statistics calculation by syncing with Backend API
  Future<void> syncStatsWithBackend() async {
    try {
      // Filter history for current selected Group
      final groupHistory = _testHistory.where((h) => h.group == _activeGroup).toList();
      final stats = await _apiService.calculateStats(groupHistory);

      _totalTests = stats['total_tests'] ?? 0;
      _totalCorrect = stats['total_correct'] ?? 0;
      _totalSolved = stats['total_solved'] ?? 0;
      _avgAccuracy = stats['avg_accuracy'] ?? 0;
      _masteryPercent = stats['mastery_percent'] ?? 0;
      _weaknessReport = stats['weakness'];
    } catch (e) {
      print("Error syncing stats with backend: $e");
    }
  }

  // Start a new test
  void startQuiz(List<Question> questions, {bool timed = false}) {
    _quizQuestions = List.from(questions);
    _currentQuestionIndex = 0;
    _selectedAnswers.clear();
    _isTimed = timed;
    _quizInProgress = true;
    _activeScreen = 'quiz';
    _timeTakenSeconds = 0;

    _questionFirstViewedAt.clear();
    _questionResponseTimeMs.clear();
    _questionFirstViewedAt[0] = DateTime.now();

    unawaited(_apiService.logEvent(_userEmail, 'quiz_started', {
      'topic': _resolveTopicName(),
      'question_count': questions.length,
    }));

    if (timed) {
      _remainingSeconds = 1800; // 30 mins
      _quizTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (_remainingSeconds > 0) {
          _remainingSeconds--;
          _timeTakenSeconds++;
          notifyListeners();
        } else {
          submitQuiz();
        }
      });
    } else {
      _quizTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        _timeTakenSeconds++;
      });
    }
    notifyListeners();
  }

  void selectOption(String optionKey) {
    _selectedAnswers[_currentQuestionIndex] = optionKey;

    // Record time-to-first-answer for this question, used for admin analytics.
    if (!_questionResponseTimeMs.containsKey(_currentQuestionIndex)) {
      final firstViewed = _questionFirstViewedAt[_currentQuestionIndex];
      if (firstViewed != null) {
        _questionResponseTimeMs[_currentQuestionIndex] =
            DateTime.now().difference(firstViewed).inMilliseconds;
      }
    }
    notifyListeners();
  }

  void nextQuestion() {
    if (_currentQuestionIndex < _quizQuestions.length - 1) {
      _currentQuestionIndex++;
      _questionFirstViewedAt.putIfAbsent(_currentQuestionIndex, () => DateTime.now());
      notifyListeners();
    }
  }

  void prevQuestion() {
    if (_currentQuestionIndex > 0) {
      _currentQuestionIndex--;
      _questionFirstViewedAt.putIfAbsent(_currentQuestionIndex, () => DateTime.now());
      notifyListeners();
    }
  }

  void quitQuiz() {
    final topic = _resolveTopicName();
    final answered = _selectedAnswers.values.where((v) => v != 'E' && v.isNotEmpty).length;
    unawaited(_apiService.logEvent(_userEmail, 'quiz_abandoned', {
      'topic': topic,
      'answered_count': answered,
      'question_count': _quizQuestions.length,
      'time_taken': _timeTakenSeconds,
    }));

    _quizTimer?.cancel();
    _quizInProgress = false;
    _activeScreen = 'topic_detail';
    notifyListeners();
  }

  /// Single source of truth for the "topic" label attached to quiz_started /
  /// quiz_completed events and saved sessions, so admin analytics can match
  /// funnel events (started vs completed) by an identical topic string.
  String _resolveTopicName() {
    return _activeTopic ??
        (_activeSubject == 'Economy'
            ? 'Indian Economy'
            : _activeSubject == 'Polity'
                ? 'Indian Polity'
                : _activeSubject == 'Policy'
                    ? 'Policy Notes'
                    : _activeSubject == 'History'
                        ? 'Indian History'
                        : _activeSubject == 'INM'
                            ? 'Indian National Movement'
                            : _activeSubject == 'Chemistry'
                                ? 'Chemistry'
                                : _activeSubject == 'TVK'
                                    ? 'TVK-Government Policies'
                                    : _activeSubject == 'CGS'
                                        ? 'Central Government Schemes'
                                        : _activeSubject == 'Tamil'
                                            ? 'Tamil'
                                            : 'Current Affairs');
  }

  // Submit test session
  Future<void> submitQuiz() async {
    _quizTimer?.cancel();
    _quizInProgress = false;

    // Calculate score
    int correct = 0;
    Map<String, String> sessionAnswers = {};
    for (int i = 0; i < _quizQuestions.length; i++) {
      String selected = _selectedAnswers[i] ?? 'E'; // Default Option E
      sessionAnswers[i.toString()] = selected;
      if (selected == _quizQuestions[i].correctOption) {
        correct++;
      }
    }

    String sessionBatch = '';
    for (final q in _quizQuestions) {
      if (q.type.toLowerCase() != 'pyq' && q.batch.trim().isNotEmpty) {
        sessionBatch = q.batch.trim();
        break;
      }
    }

    final newSession = HistoryEntry(
      topic: _resolveTopicName(),
      group: _activeGroup,
      correctCount: correct,
      totalCount: _quizQuestions.length,
      answers: sessionAnswers,
      questions: _quizQuestions,
      timestamp: DateTime.now().millisecondsSinceEpoch.toDouble(),
      batch: sessionBatch,
    );

    _testHistory.add(newSession);
    _lastCompletedSession = newSession;
    _resultsReturnScreen = 'topic_detail';
    _activeScreen = 'results';

    List<Map<String, dynamic>> backendAnswers = [];
    for (int i = 0; i < _quizQuestions.length; i++) {
      String selected = _selectedAnswers[i] ?? 'E';
      backendAnswers.add({
        'question_id': _quizQuestions[i].id ?? 0,
        'selected_option': selected,
        'is_correct': selected == _quizQuestions[i].correctOption,
        'response_time_ms': _questionResponseTimeMs[i],
      });
    }

    _apiService.submitSession(
      userId: _userEmail,
      topicName: newSession.topic,
      correctCount: correct,
      totalCount: _quizQuestions.length,
      timeTaken: _timeTakenSeconds,
      answers: backendAnswers,
      batch: sessionBatch.isNotEmpty ? sessionBatch : null,
    ).then((res) {
      print("Session saved successfully on server. ID: ${res['session_id']}");
    }).catchError((err) {
      print("Error saving session to server: $err");
    });

    await saveLocalPreferences();
    await syncStatsWithBackend();
    notifyListeners();
  }

  Future<void> signInWithGoogle() async {
    _loading = true;
    notifyListeners();
    try {
      final GoogleSignInAccount? googleUser = await GoogleSignIn.instance.authenticate();
      if (googleUser != null) {
        final GoogleSignInAuthentication googleAuth = googleUser.authentication;
        final String? idToken = googleAuth.idToken;

        print("Logged in successfully: ${googleUser.email}");
        print("ID Token: $idToken");

        _userEmail = googleUser.email;
        _isAuthenticated = true;
        _activeScreen = 'home';
        await saveLocalPreferences();

        unawaited(_apiService.logEvent(_userEmail, 'sign_in', {'method': 'google'}));
        unawaited(_apiService.updateDeviceInfo(
          userId: _userEmail,
          displayName: googleUser.displayName,
        ));
        unawaited(_logAppOpenAndSyncDevice());
      }
    } catch (e) {
      print("Google Sign-In Error: $e");
      rethrow;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Web / local preview path — same idea as the old app.js (no Google gate).
  Future<void> signInAsGuest() async {
    _loading = true;
    notifyListeners();
    try {
      _userEmail = 'test_user';
      _isAuthenticated = true;
      _activeScreen = 'home';
      await saveLocalPreferences();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    final email = _userEmail;
    try {
      if (_isAuthenticated && email != 'test_user') {
        unawaited(_apiService.logEvent(email, 'sign_out'));
      }
      await GoogleSignIn.instance.signOut();
    } catch (e) {
      print("Google Sign-Out Error: $e");
    }
    _isAuthenticated = false;
    _activeScreen = 'home';
    _activeSubject = null;
    _activeTopic = null;
    _quizInProgress = false;
    _quizTimer?.cancel();
    _selectedAnswers.clear();
    await saveLocalPreferences();
    notifyListeners();
  }

  Future<void> deleteUserAccount() async {
    _loading = true;
    notifyListeners();
    try {
      await _apiService.deleteAccount(_userEmail);
      print("Account deleted successfully on server database.");
    } catch (e) {
      print("Error deleting account from server: $e");
    } finally {
      _loading = false;
      await signOut();
    }
  }
}

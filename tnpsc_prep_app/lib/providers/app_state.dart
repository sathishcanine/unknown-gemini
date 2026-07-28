import 'dart:async';
import 'dart:convert';
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

  // Auth State
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

  // Subjects / Syllabus loaded from backend
  List<Map<String, dynamic>> _subjects = [];
  List<Map<String, dynamic>> get subjects => _subjects;

  List<Map<String, dynamic>> _syllabusList = [];
  List<Map<String, dynamic>> get syllabusList => _syllabusList;

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
    notifyListeners();

    try {
      await GoogleSignIn.instance.initialize(
        clientId: '81319537728-a3cnfl5nn2e43g27rqd8tc2p239ij403.apps.googleusercontent.com',
        serverClientId: '81319537728-9jba22kbo57fa1c7f9q9bje69r5173m1.apps.googleusercontent.com',
      );
    } catch (e) {
      print("Google Sign-In Init Error: $e");
    }

    await loadLocalPreferences();
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

    final historyJson = jsonEncode(_testHistory.map((h) => h.toJson()).toList());
    await prefs.setString('test_history', historyJson);
  }

  Future<void> toggleTheme() async {
    _isDarkMode = !_isDarkMode;
    await saveLocalPreferences();
    notifyListeners();
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
    notifyListeners();
  }

  void navigateToSyllabus() {
    if (_activeSubject != null) {
      _activeScreen = 'syllabus';
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

    final newSession = HistoryEntry(
      topic: _resolveTopicName(),
      group: _activeGroup,
      correctCount: correct,
      totalCount: _quizQuestions.length,
      answers: sessionAnswers,
      questions: _quizQuestions,
      timestamp: DateTime.now().millisecondsSinceEpoch.toDouble(),
    );

    _testHistory.add(newSession);
    _lastCompletedSession = newSession;
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
        final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
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

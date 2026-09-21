import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;
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

  static const _guestIdKey = 'guest_user_id';
  static const _whatsAppNumberKey = 'whatsapp_number';
  static const _whatsAppCollectedKey = 'whatsapp_collected';

  String _userEmail = 'test_user';
  String get userEmail => _userEmail;

  String? _whatsAppNumber;
  String? get whatsAppNumber => _whatsAppNumber;

  /// True until the user saves a WhatsApp number or taps "I'll do this later".
  bool _whatsAppCollected = false;
  bool get needsWhatsAppNumber =>
      _isAuthenticated && _authReady && !_whatsAppCollected;

  bool get isGuestUser {
    final email = _userEmail.toLowerCase();
    return email.endsWith('@guest.local') || email == 'test_user';
  }

  String? _activeTopic;
  String? get activeTopic => _activeTopic;

  bool _isDarkMode = true;
  bool get isDarkMode => _isDarkMode;

  // Content language for menus/titles from API (en | ta)
  String _contentLanguage = 'en';
  String get contentLanguage => _contentLanguage;
  bool get isTamilContent => _contentLanguage == 'ta';

  /// Podhu Tamil / General English are monolingual (exam language), not toggle-driven.
  bool get isEnglishSection =>
      _activeSubject == 'English' ||
      _tamilHubLevel == 'english_units' ||
      _tamilHubLevel == 'english_menus' ||
      _tamilHubLevel == 'english_groups';

  bool get isTamilSection =>
      _activeSubject == 'Tamil' || _tamilHubLevel == 'units';

  /// UI language for labels: Tamil section → always TA; English section → always EN;
  /// otherwise follow the content-language toggle (GS / CA / etc.).
  bool get useTamilUi {
    if (isEnglishSection) return false;
    if (isTamilSection) return true;
    return isTamilContent;
  }

  /// Quiz/results: show EN+TA only for bilingual GS-style subjects.
  bool get showBilingualQuestions =>
      !isEnglishSection && !isTamilSection && _activeSubject != 'English' && _activeSubject != 'Tamil';

  /// General English is English-only (exam paper language) — never show Tamil text.
  bool get isGeneralEnglish =>
      _activeSubject == 'English' || isEnglishSection;

  String displayQuestionText(Question q) {
    if (_activeSubject == 'Tamil' || isTamilSection) {
      return q.questionTa.isNotEmpty ? q.questionTa : q.questionEn;
    }
    return q.questionEn;
  }

  String displayOptionText(Option opt) {
    if (_activeSubject == 'Tamil' || isTamilSection) {
      return opt.textTa.isNotEmpty ? opt.textTa : opt.textEn;
    }
    return opt.textEn;
  }

  String displayExplanationText(Question q) {
    if (_activeSubject == 'Tamil' || isTamilSection) {
      return q.explanationTa.isNotEmpty ? q.explanationTa : q.explanation;
    }
    return q.explanation;
  }

  /// Hide EN/TA toggle inside monolingual Tamil & English hub flows.
  bool get showContentLanguageToggle =>
      !isEnglishSection && !isTamilSection;

  // Subjects / Syllabus loaded from backend
  List<Map<String, dynamic>> _subjects = [];
  List<Map<String, dynamic>> get subjects => _subjects;

  List<Map<String, dynamic>> _syllabusList = [];
  List<Map<String, dynamic>> get syllabusList => _syllabusList;

  /// Tamil & English hub: null | `languages` | `units` | `english_units` | `english_menus` | `english_groups`
  String? _tamilHubLevel;
  String? get tamilHubLevel => _tamilHubLevel;

  /// Selected General Tamil unit id from API (e.g. `Kalaichorkal`).
  String? _tamilUnitId;
  String? get tamilUnitId => _tamilUnitId;

  /// Selected General English unit / menu / group.
  String? _englishUnitId;
  String? get englishUnitId => _englishUnitId;

  String? _englishMenuId;
  String? get englishMenuId => _englishMenuId;

  String? _englishGroupId;
  String? get englishGroupId => _englishGroupId;

  /// Unit had a single topic — skipped syllabus and opened batches directly.
  bool _directTopicFromUnit = false;
  bool get directTopicFromUnit => _directTopicFromUnit;

  /// Server-driven Podhu Tamil units (`GET /api/tamil/units`).
  List<Map<String, dynamic>> _tamilUnits = [];
  List<Map<String, dynamic>> get tamilUnits => _tamilUnits;

  /// Server-driven General English units (`GET /api/english/units`).
  List<Map<String, dynamic>> _englishUnits = [];
  List<Map<String, dynamic>> get englishUnits => _englishUnits;

  Map<String, dynamic>? get selectedTamilUnit {
    if (_tamilUnitId == null) return null;
    for (final u in _tamilUnits) {
      if ((u['id'] ?? '').toString() == _tamilUnitId) return u;
    }
    return null;
  }

  Map<String, dynamic>? get selectedEnglishUnit {
    if (_englishUnitId == null) return null;
    for (final u in _englishUnits) {
      if ((u['id'] ?? '').toString() == _englishUnitId) return u;
    }
    return null;
  }

  Map<String, dynamic>? get selectedEnglishMenu {
    final unit = selectedEnglishUnit;
    if (unit == null || _englishMenuId == null) return null;
    final raw = unit['menus'];
    if (raw is! List) return null;
    for (final m in raw) {
      if (m is Map && (m['id'] ?? '').toString() == _englishMenuId) {
        return Map<String, dynamic>.from(m);
      }
    }
    return null;
  }

  Map<String, dynamic>? get selectedEnglishGroup {
    final menu = selectedEnglishMenu;
    if (menu == null || _englishGroupId == null) return null;
    final raw = menu['groups'];
    if (raw is! List) return null;
    for (final g in raw) {
      if (g is Map && (g['id'] ?? '').toString() == _englishGroupId) {
        return Map<String, dynamic>.from(g);
      }
    }
    return null;
  }

  /// Syllabus rows visible for the current Tamil/English filter (or full list).
  List<Map<String, dynamic>> get visibleSyllabusList {
    if (_activeSubject == 'Tamil' && _tamilUnitId != null) {
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
    if (_activeSubject == 'English') {
      // Tenses: only show topics for the selected group (never all 13 forms).
      if (_englishMenuHasGroups(selectedEnglishMenu ?? findEnglishMenu(_englishMenuId ?? ''))) {
        final group = selectedEnglishGroup;
        if (group == null) return [];
        final raw = group['topics'];
        final names = <String>{
          if (raw is List) ...raw.map((e) => e.toString()),
        };
        if (names.isEmpty) return _syllabusList;
        return _syllabusList
            .where((t) => names.contains((t['name'] ?? '').toString()))
            .toList();
      }
      final src = selectedEnglishMenu;
      if (src != null) {
        final raw = src['topics'];
        final names = <String>{
          if (raw is List) ...raw.map((e) => e.toString()),
        };
        if (names.isNotEmpty) {
          return _syllabusList
              .where((t) => names.contains((t['name'] ?? '').toString()))
              .toList();
        }
      }
    }
    return _syllabusList;
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

  String englishUnitDisplayName(String? unitId) {
    if (unitId == null || unitId.isEmpty) return '';
    for (final u in _englishUnits) {
      if ((u['id'] ?? '').toString() == unitId) {
        return (u['name_en'] ?? u['name_ta'] ?? unitId).toString();
      }
    }
    return unitId;
  }

  String englishMenuDisplayName(String? menuId) {
    if (menuId == null || menuId.isEmpty) return '';
    final menu = selectedEnglishMenu;
    if (menu != null && (menu['id'] ?? '').toString() == menuId) {
      return (menu['name_en'] ?? menu['name_ta'] ?? menuId).toString();
    }
    for (final u in _englishUnits) {
      final menus = u['menus'];
      if (menus is! List) continue;
      for (final m in menus) {
        if (m is Map && (m['id'] ?? '').toString() == menuId) {
          return (m['name_en'] ?? m['name_ta'] ?? menuId).toString();
        }
      }
    }
    return menuId;
  }

  String englishHubSubtitle(Map<String, dynamic> item) {
    final en = (item['subtitle_en'] ?? '').toString().trim();
    if (en.isNotEmpty) return en;
    final ta = (item['subtitle_ta'] ?? '').toString().trim();
    if (ta.isNotEmpty) return ta;
    final tc = item['topic_count'] ?? item['menu_count'];
    final qc = item['questions_count'];
    if (tc != null || qc != null) {
      return '${tc ?? 0} items · ${qc ?? 0} Q';
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

  int _remainingSeconds = 1200; // 20 minutes default
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
      if (_isAuthenticated && _userEmail.isNotEmpty && _userEmail != 'test_user') {
        await _apiService.logEvent(_userEmail, 'app_open');
      }
    } catch (e) {
      debugPrint('Analytics init failed silently: $e');
    }
  }

  String _generateGuestUserId() {
    final rand = Random.secure();
    final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
    final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return 'guest_$hex@guest.local';
  }

  /// Stable per-device guest identity so returning guests map to the same backend user.
  Future<String> _ensureGuestUserId() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(_guestIdKey);
    if (stored != null && stored.endsWith('@guest.local')) {
      return stored;
    }
    if (_userEmail.endsWith('@guest.local')) {
      await prefs.setString(_guestIdKey, _userEmail);
      return _userEmail;
    }
    final guestId = _generateGuestUserId();
    await prefs.setString(_guestIdKey, guestId);
    return guestId;
  }

  // Load preferences from local storage
  Future<void> loadLocalPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    _activeGroup = prefs.getString('active_group') ?? 'Group 1';
    _isAuthenticated = prefs.getBool('is_authenticated') ?? false;
    _userEmail = prefs.getString('user_email') ?? 'test_user';
    _contentLanguage = prefs.getString('content_language') ?? 'en';
    _whatsAppNumber = prefs.getString(_whatsAppNumberKey);
    _whatsAppCollected = prefs.getBool(_whatsAppCollectedKey) ?? false;

    // Release builds retire guest login: clear any persisted guest session so
    // the user must sign in with Google. Debug builds keep guest sessions.
    if (!kDebugMode && _isAuthenticated && isGuestUser) {
      _isAuthenticated = false;
      _userEmail = 'test_user';
      await prefs.setBool('is_authenticated', false);
      await prefs.remove('user_email');
      await prefs.remove(_guestIdKey);
      await prefs.remove(_whatsAppNumberKey);
      await prefs.setBool(_whatsAppCollectedKey, false);
      _whatsAppNumber = null;
      _whatsAppCollected = false;
    }

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
    await prefs.setBool(_whatsAppCollectedKey, _whatsAppCollected);
    if (_whatsAppNumber != null && _whatsAppNumber!.isNotEmpty) {
      await prefs.setString(_whatsAppNumberKey, _whatsAppNumber!);
    } else {
      await prefs.remove(_whatsAppNumberKey);
    }

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
    // General English stays English; Podhu Tamil stays Tamil.
    if (subjectId == 'English' || isEnglishSection) {
      return (match['name'] ?? subjectId ?? '').toString();
    }
    if (subjectId == 'Tamil' || isTamilSection || useTamilUi) {
      final ta = (match['name_ta'] ?? '').toString().trim();
      if (ta.isNotEmpty) return ta;
    }
    return (match['name'] ?? subjectId ?? '').toString();
  }

  /// Topic title from syllabus item: EN `name` or API `textbook.titleTa`.
  String topicDisplayNameFromItem(Map<String, dynamic> item) {
    final en = (item['name'] ?? '').toString();
    if (isEnglishSection || _activeSubject == 'English') return en;
    if (!useTamilUi) return en;
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
    if (isGeneralEnglish) return english;
    if (isTamilSection || _activeSubject == 'Tamil') {
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
    if (!useTamilUi) return english;
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
    // Leaving Tamil/English hub when opening any other subject path.
    if (subjectId != 'Tamil' && subjectId != 'English') {
      _tamilHubLevel = null;
      _tamilUnitId = null;
      _englishUnitId = null;
      _englishMenuId = null;
      _englishGroupId = null;
    }
    if (subjectId == 'English') {
      // Flat English entry (legacy) — prefer nested hub via openGeneralEnglishUnits.
      _englishUnitId = null;
      _englishMenuId = null;
      _englishGroupId = null;
    }
    _activeSubject = subjectId;
    _activeTopic = null;
    _directTopicFromUnit = false;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      _syllabusList = await _apiService.getSyllabus(subjectId);
      // Aptitude has a single topic — open batches directly (no syllabus submenu).
      if (subjectId == 'Aptitude' && _syllabusList.length == 1) {
        final name = (_syllabusList.first['name'] ?? '').toString();
        if (name.isNotEmpty) {
          _activeTopic = name;
          _directTopicFromUnit = true;
          _activeScreen = 'topic_detail';
        }
      }
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
    _englishUnitId = null;
    _englishMenuId = null;
    _englishGroupId = null;
    _activeSubject = null;
    _activeTopic = null;
    _activeScreen = 'home';
    notifyListeners();
  }

  Future<void> openGeneralTamilUnits() async {
    _tamilHubLevel = 'units';
    _tamilUnitId = null;
    _englishUnitId = null;
    _englishMenuId = null;
    _englishGroupId = null;
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

  Future<void> openGeneralEnglishUnits() async {
    _tamilHubLevel = 'english_units';
    _tamilUnitId = null;
    _englishUnitId = null;
    _englishMenuId = null;
    _englishGroupId = null;
    _activeSubject = null;
    _activeTopic = null;
    _activeScreen = 'home';
    _loading = true;
    notifyListeners();
    try {
      _englishUnits = await _apiService.getEnglishUnits();
    } catch (e) {
      print("Error fetching English units: $e");
      _englishUnits = [];
    }
    _loading = false;
    notifyListeners();
  }

  void openEnglishUnitMenus(String unitId) {
    _englishUnitId = unitId;
    _englishMenuId = null;
    _englishGroupId = null;
    _tamilHubLevel = 'english_menus';
    _activeSubject = null;
    _activeTopic = null;
    _activeScreen = 'home';
    notifyListeners();
  }

  /// Find a menu by id across loaded English units (does not require unit id set).
  Map<String, dynamic>? findEnglishMenu(String menuId) {
    for (final u in _englishUnits) {
      final menus = u['menus'];
      if (menus is! List) continue;
      for (final m in menus) {
        if (m is Map && (m['id'] ?? '').toString() == menuId) {
          return Map<String, dynamic>.from(m);
        }
      }
    }
    return null;
  }

  bool _englishMenuHasGroups(Map<String, dynamic>? menu) {
    if (menu == null) return false;
    final groups = menu['groups'];
    if (groups is List && groups.isNotEmpty) return true;
    final count = menu['group_count'];
    if (count is num && count > 0) return true;
    return false;
  }

  Future<void> selectEnglishMenu(String menuId) async {
    _englishMenuId = menuId;
    _englishGroupId = null;
    _directTopicFromUnit = false;

    // Prefer explicit lookup so nested Tenses groups are never skipped.
    final menu = selectedEnglishMenu ?? findEnglishMenu(menuId);
    if (menu != null && _englishUnitId == null) {
      for (final u in _englishUnits) {
        final menus = u['menus'];
        if (menus is! List) continue;
        final hit = menus.any(
          (m) => m is Map && (m['id'] ?? '').toString() == menuId,
        );
        if (hit) {
          _englishUnitId = (u['id'] ?? '').toString();
          break;
        }
      }
    }

    // Nested groups (Tenses → Present/Past/Future/Mixed) — stay on hub.
    if (_englishMenuHasGroups(menu)) {
      _tamilHubLevel = 'english_groups';
      _activeSubject = null;
      _activeTopic = null;
      _activeScreen = 'home';
      _syllabusList = [];
      notifyListeners();
      return;
    }

    _tamilHubLevel = 'english_menus';
    _activeSubject = 'English';
    _activeTopic = null;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      _syllabusList = await _apiService.getSyllabus('English', menu: menuId);
      if (_syllabusList.isEmpty) {
        _syllabusList = await _apiService.getSyllabus('English');
      }
      final topics = visibleSyllabusList;
      if (topics.length == 1) {
        final name = (topics.first['name'] ?? '').toString();
        if (name.isNotEmpty) {
          _activeTopic = name;
          _directTopicFromUnit = true;
          _activeScreen = 'topic_detail';
        }
      }
    } catch (e) {
      print("Error fetching English syllabus for menu $menuId: $e");
      _syllabusList = [];
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> selectEnglishGroup(String groupId) async {
    _englishGroupId = groupId;
    _tamilHubLevel = 'english_groups';
    _activeSubject = 'English';
    _activeTopic = null;
    _directTopicFromUnit = false;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      _syllabusList = await _apiService.getSyllabus(
        'English',
        menu: _englishMenuId,
        group: groupId,
      );
      if (_syllabusList.isEmpty) {
        _syllabusList = await _apiService.getSyllabus('English');
      }
      final topics = visibleSyllabusList;
      if (topics.length == 1) {
        final name = (topics.first['name'] ?? '').toString();
        if (name.isNotEmpty) {
          _activeTopic = name;
          _directTopicFromUnit = true;
          _activeScreen = 'topic_detail';
        }
      }
    } catch (e) {
      print("Error fetching English syllabus for group $groupId: $e");
      _syllabusList = [];
    }

    _loading = false;
    notifyListeners();
  }

  /// Back within Tamil & English hub.
  /// Returns true if a hub level was popped.
  bool backTamilHub() {
    if (_tamilHubLevel == 'english_groups') {
      _tamilHubLevel = 'english_menus';
      _englishGroupId = null;
      notifyListeners();
      return true;
    }
    if (_tamilHubLevel == 'english_menus') {
      _tamilHubLevel = 'english_units';
      _englishMenuId = null;
      _englishGroupId = null;
      notifyListeners();
      return true;
    }
    if (_tamilHubLevel == 'english_units') {
      _tamilHubLevel = 'languages';
      _englishUnitId = null;
      _englishMenuId = null;
      _englishGroupId = null;
      notifyListeners();
      return true;
    }
    if (_tamilHubLevel == 'units') {
      _tamilHubLevel = 'languages';
      _tamilUnitId = null;
      notifyListeners();
      return true;
    }
    if (_tamilHubLevel == 'languages') {
      _tamilHubLevel = null;
      _tamilUnitId = null;
      _englishUnitId = null;
      _englishMenuId = null;
      _englishGroupId = null;
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
    _directTopicFromUnit = false;
    _activeScreen = 'syllabus';
    _loading = true;
    notifyListeners();

    try {
      // Prefer server-side unit filter; fall back to full syllabus + client filter.
      _syllabusList = await _apiService.getSyllabus('Tamil', unit: unitId);
      if (_syllabusList.isEmpty) {
        _syllabusList = await _apiService.getSyllabus('Tamil');
      }

      // Single-topic units (e.g. Tamilpani / Thondu / Saandror): open batches directly.
      final topics = visibleSyllabusList;
      if (topics.length == 1) {
        final name = (topics.first['name'] ?? '').toString();
        if (name.isNotEmpty) {
          _activeTopic = name;
          _directTopicFromUnit = true;
          _activeScreen = 'topic_detail';
        }
      }
    } catch (e) {
      print("Error fetching Tamil syllabus for unit $unitId: $e");
      _syllabusList = [];
    }

    _loading = false;
    notifyListeners();
  }

  /// Back from syllabus: Tamil units / English menus or groups → hub; else home root.
  void navigateBackFromSyllabus() {
    if (_activeSubject == 'Tamil' && _tamilUnitId != null) {
      _tamilUnitId = null;
      _tamilHubLevel = 'units';
      _activeSubject = null;
      _activeTopic = null;
      _directTopicFromUnit = false;
      _syllabusList = [];
      _activeScreen = 'home';
      notifyListeners();
      return;
    }
    if (_activeSubject == 'English' && _englishGroupId != null) {
      _englishGroupId = null;
      _tamilHubLevel = 'english_groups';
      _activeSubject = null;
      _activeTopic = null;
      _directTopicFromUnit = false;
      _syllabusList = [];
      _activeScreen = 'home';
      notifyListeners();
      return;
    }
    if (_activeSubject == 'English' && _englishMenuId != null) {
      _englishMenuId = null;
      _tamilHubLevel = 'english_menus';
      _activeSubject = null;
      _activeTopic = null;
      _directTopicFromUnit = false;
      _syllabusList = [];
      _activeScreen = 'home';
      notifyListeners();
      return;
    }
    navigateToHome();
  }

  void selectTopic(String topicName) {
    _activeTopic = topicName;
    _directTopicFromUnit = false;
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
    _englishUnitId = null;
    _englishMenuId = null;
    _englishGroupId = null;
    notifyListeners();
  }

  void navigateToSyllabus() {
    // Came straight from a single-topic unit/subject → back to prior list, not empty syllabus.
    if (_directTopicFromUnit &&
        (_tamilUnitId != null ||
            _englishMenuId != null ||
            _activeSubject == 'Aptitude')) {
      _directTopicFromUnit = false;
      navigateBackFromSyllabus();
      return;
    }
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
      _remainingSeconds = 1200; // 20 mins
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
    // In Learn Mode, lock the first selection so right/wrong feedback stays visible.
    if (!_isTimed && _selectedAnswers.containsKey(_currentQuestionIndex)) {
      return;
    }

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
                                            : _activeSubject == 'English'
                                                ? 'General English'
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

        final previousEmail = _userEmail;
        final hadCollected = _whatsAppCollected;
        final hadNumber = _whatsAppNumber;

        _userEmail = googleUser.email;
        _isAuthenticated = true;
        _activeScreen = 'home';
        // Re-prompt only for a different account; keep number for same user.
        if (previousEmail != _userEmail || !hadCollected) {
          _whatsAppCollected = false;
          _whatsAppNumber = null;
        } else {
          _whatsAppCollected = hadCollected;
          _whatsAppNumber = hadNumber;
        }
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

  Future<void> signInAsGuest() async {
    _loading = true;
    notifyListeners();
    try {
      final previousEmail = _userEmail;
      final hadCollected = _whatsAppCollected;
      final hadNumber = _whatsAppNumber;

      _userEmail = await _ensureGuestUserId();
      _isAuthenticated = true;
      _activeScreen = 'home';
      // Guest path shows WhatsApp screen for testing; same guest keeps prior choice.
      if (previousEmail != _userEmail || !hadCollected) {
        _whatsAppCollected = false;
        _whatsAppNumber = null;
      } else {
        _whatsAppCollected = hadCollected;
        _whatsAppNumber = hadNumber;
      }
      await saveLocalPreferences();

      unawaited(_apiService.logEvent(_userEmail, 'sign_in', {'method': 'guest'}));
      unawaited(_apiService.updateDeviceInfo(
        userId: _userEmail,
        displayName: 'Guest',
      ));
      unawaited(_logAppOpenAndSyncDevice());
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> saveWhatsAppNumber(String digits) async {
    final normalized = digits.trim();
    _whatsAppNumber = normalized;
    _whatsAppCollected = true;
    // Local first so UI unlocks immediately; API sync is background-only.
    await saveLocalPreferences();
    notifyListeners();

    unawaited(_apiService.logEvent(_userEmail, 'whatsapp_number_saved', {
      'digits': normalized.length,
    }));
    unawaited(_apiService.saveWhatsAppNumber(
      userId: _userEmail,
      phoneNumber: normalized,
    ));
  }

  Future<void> skipWhatsAppNumber() async {
    _whatsAppCollected = true;
    await saveLocalPreferences();
    notifyListeners();
    unawaited(_apiService.logEvent(_userEmail, 'whatsapp_number_skipped'));
  }

  Future<void> signOut() async {
    final email = _userEmail;
    final wasGuest = isGuestUser;
    try {
      if (_isAuthenticated && email.isNotEmpty && email != 'test_user') {
        unawaited(_apiService.logEvent(email, 'sign_out'));
      }
      if (!wasGuest && !kIsWeb) {
        await GoogleSignIn.instance.signOut();
      }
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
    _whatsAppNumber = null;
    _whatsAppCollected = false;
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
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_guestIdKey);
      await signOut();
    }
  }
}

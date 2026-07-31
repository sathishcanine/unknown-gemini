import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../models/question.dart';
import '../services/api_service.dart';

class TopicDetailScreen extends StatefulWidget {
  const TopicDetailScreen({Key? key}) : super(key: key);

  @override
  State<TopicDetailScreen> createState() => _TopicDetailScreenState();
}

class _TopicDetailScreenState extends State<TopicDetailScreen> {
  final ApiService _apiService = ApiService();
  List<Question> _allQuestions = [];
  bool _loading = true;
  String _errorMsg = '';
  /// Normalized batch key -> latest completion stats from API
  final Map<String, Map<String, dynamic>> _completedByBatch = {};

  @override
  void initState() {
    super.initState();
    _loadQuestions();
  }

  Future<void> _loadQuestions() async {
    final appState = Provider.of<AppState>(context, listen: false);
    setState(() {
      _loading = true;
      _errorMsg = '';
    });

    try {
      final qs = await _apiService.getQuestions(
        subject: appState.activeSubject ?? 'Economy',
        topic: appState.activeTopic,
      );
      await _loadCompletedBatches(appState);
      setState(() {
        _allQuestions = qs;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _errorMsg = 'Failed to load questions from backend. Make sure FastAPI server is running.';
        _loading = false;
      });
    }
  }

  Future<void> _loadCompletedBatches(AppState appState) async {
    final topic = appState.activeTopic;
    if (topic == null || topic.isEmpty) return;

    // Seed from local history first.
    _completedByBatch.clear();
    for (final key in appState.localCompletedBatchKeys(topic)) {
      final local = appState.latestLocalBatchSession(topic, key);
      _completedByBatch[key] = {
        'batch': key,
        'correct_count': local?.correctCount ?? 0,
        'total_count': local?.totalCount ?? 0,
      };
    }

    try {
      final remote = await _apiService.getCompletedBatches(
        userId: appState.userEmail,
        topic: topic,
      );
      for (final item in remote) {
        final key = appState.normalizeBatchKey(item['batch']?.toString());
        if (key.isEmpty) continue;
        _completedByBatch[key] = item;
      }
    } catch (e) {
      // Local history still drives Completed section if API is unavailable.
      debugPrint('Completed batches fetch failed: $e');
    }
  }

  bool _isBatchCompleted(AppState appState, String batchKey) {
    final key = appState.normalizeBatchKey(batchKey);
    if (_completedByBatch.containsKey(key)) return true;
    final topic = appState.activeTopic;
    if (topic == null) return false;
    return appState.localCompletedBatchKeys(topic).contains(key);
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = appState.isDarkMode;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);
    final mutedColor = isDark ? Colors.grey : const Color(0xFF64748B);
    final cardBg = isDark ? const Color(0xFF131A2A) : Colors.white;
    final scaffoldBg = isDark ? const Color(0xFF0B0F19) : const Color(0xFFF1F5F9);

    final topicName = appState.activeTopicDisplayName();

    // Group questions by type / batch
    final pyqList = _allQuestions.where((q) => q.type.toLowerCase() == 'pyq').toList();
    
    // Group practice batches
    final batchesMap = <String, List<Question>>{};
    for (var q in _allQuestions) {
      if (q.type.toLowerCase() != 'pyq') {
        final bName = q.batch.isNotEmpty ? q.batch : '1';
        batchesMap.putIfAbsent(bName, () => []).add(q);
      }
    }
    final sortedBatchKeys = batchesMap.keys.toList()..sort();
    final availableBatchKeys = sortedBatchKeys
        .where((k) => !_isBatchCompleted(appState, k))
        .toList();
    final completedBatchKeys = sortedBatchKeys
        .where((k) => _isBatchCompleted(appState, k))
        .toList();

    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        backgroundColor: scaffoldBg,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: textColor),
          onPressed: () => appState.navigateToSyllabus(),
        ),
        title: Text(
          topicName,
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 16,
            color: textColor,
          ),
        ),
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF3B82F6)),
              ),
            )
          : _errorMsg.isNotEmpty
              ? Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        '🔌 Connection Error',
                        style: TextStyle(
                            fontFamily: 'Outfit', fontSize: 18, color: Colors.red),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        _errorMsg,
                        textAlign: TextAlign.center,
                        style: TextStyle(fontFamily: 'Inter', color: mutedColor),
                      ),
                      const SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: _loadQuestions,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // 1. PYQs Card — hide entirely when this topic has no PYQs
                      if (pyqList.isNotEmpty) ...[
                        Text(
                          'Previous Year Questions',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Card(
                          color: cardBg,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                            side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.blue.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: const Text('📋', style: TextStyle(fontSize: 22)),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        'TNPSC Exam PYQs',
                                        style: TextStyle(
                                          fontFamily: 'Outfit',
                                          fontSize: 15,
                                          fontWeight: FontWeight.bold,
                                          color: textColor,
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        '${pyqList.length} PYQs Available',
                                        style: TextStyle(
                                          fontFamily: 'Inter',
                                          fontSize: 12,
                                          color: mutedColor,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                ElevatedButton(
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF3B82F6),
                                    foregroundColor: Colors.white,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    elevation: 0,
                                  ),
                                  onPressed: () => _showStartDialog(pyqList),
                                  child: const Text(
                                    'Practice',
                                    style: TextStyle(
                                      fontFamily: 'Inter',
                                      fontWeight: FontWeight.bold,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 28),
                      ],

                      // 2. Available Practice Batches
                      if (sortedBatchKeys.isEmpty)
                        Center(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 24.0),
                            child: Text(
                              'No practice batches available for this topic yet.',
                              style: TextStyle(fontFamily: 'Inter', color: mutedColor),
                            ),
                          ),
                        )
                      else ...[
                        Text(
                          appState.hubLabel('Practice Batches'),
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        const SizedBox(height: 12),
                        if (availableBatchKeys.isEmpty)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              'All batches completed for this topic.',
                              style: TextStyle(fontFamily: 'Inter', color: mutedColor, fontSize: 13),
                            ),
                          )
                        else
                          _buildBatchPanel(
                            appState: appState,
                            batchKeys: availableBatchKeys,
                            batchesMap: batchesMap,
                            textColor: textColor,
                            mutedColor: mutedColor,
                            isDark: isDark,
                            cardBg: cardBg,
                            completed: false,
                          ),
                        if (completedBatchKeys.isNotEmpty) ...[
                          const SizedBox(height: 28),
                          Text(
                            appState.hubLabel('Completed'),
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: textColor,
                            ),
                          ),
                          const SizedBox(height: 12),
                          _buildBatchPanel(
                            appState: appState,
                            batchKeys: completedBatchKeys,
                            batchesMap: batchesMap,
                            textColor: textColor,
                            mutedColor: mutedColor,
                            isDark: isDark,
                            cardBg: cardBg,
                            completed: true,
                          ),
                        ],
                      ],
                    ],
                  ),
                ),
    );
  }

  Widget _buildBatchPanel({
    required AppState appState,
    required List<String> batchKeys,
    required Map<String, List<Question>> batchesMap,
    required Color textColor,
    required Color mutedColor,
    required bool isDark,
    required Color cardBg,
    required bool completed,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.06) : Colors.black.withOpacity(0.05),
        ),
      ),
      child: Column(
        children: [
          for (int index = 0; index < batchKeys.length; index++) ...[
            if (index > 0)
              Divider(
                height: 1,
                thickness: 1,
                color: isDark ? Colors.white.withOpacity(0.06) : Colors.black.withOpacity(0.05),
              ),
            _buildPracticeBatchRow(
              appState: appState,
              index: index,
              batchKey: batchKeys[index],
              questions: batchesMap[batchKeys[index]]!,
              textColor: textColor,
              mutedColor: mutedColor,
              isDark: isDark,
              completed: completed,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPracticeBatchRow({
    required AppState appState,
    required int index,
    required String batchKey,
    required List<Question> questions,
    required Color textColor,
    required Color mutedColor,
    required bool isDark,
    required bool completed,
  }) {
    final number = (() {
      final m = RegExp(r'(\d+)').firstMatch(batchKey);
      return (m?.group(1) ?? '${index + 1}').padLeft(2, '0');
    })();
    final accent = completed ? const Color(0xFF3B82F6) : const Color(0xFF10B981);
    final norm = appState.normalizeBatchKey(batchKey);
    final stats = _completedByBatch[norm];
    final scoreText = (completed && stats != null)
        ? '${stats['correct_count'] ?? 0}/${stats['total_count'] ?? questions.length} · ${appState.hubLabel('Completed')}'
        : appState.questionsAvailableLabel(questions.length);

    return InkWell(
      onTap: () => _showStartDialog(questions),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                color: accent.withOpacity(0.12),
              ),
              child: completed
                  ? Icon(Icons.check_rounded, color: accent, size: 22)
                  : Text(
                      number,
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: accent,
                      ),
                    ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    appState.practiceBatchLabel(batchKey),
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: textColor,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    scoreText,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 12,
                      color: mutedColor,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: accent,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                appState.hubLabel(completed ? 'Retake' : 'Start'),
                style: const TextStyle(
                  fontFamily: 'Inter',
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showStartDialog(List<Question> questions) {
    final appState = Provider.of<AppState>(context, listen: false);
    final isDark = appState.isDarkMode;
    final bSheetBg = isDark ? const Color(0xFF0F172A) : Colors.white;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);
    final mutedColor = isDark ? Colors.grey : const Color(0xFF64748B);
    final buttonBg = isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0);
    final buttonText = isDark ? Colors.white : const Color(0xFF475569);
    final buttonBorder = isDark ? Colors.white10 : Colors.black12;

    showModalBottomSheet(
      context: context,
      backgroundColor: bSheetBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Start Practice Session',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Choose your exam mode for this session (${questions.length} questions):',
                textAlign: TextAlign.center,
                style: TextStyle(fontFamily: 'Inter', color: mutedColor, fontSize: 13),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: buttonBg,
                        foregroundColor: buttonText,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(color: buttonBorder),
                        ),
                        elevation: 0,
                      ),
                      onPressed: () {
                        Navigator.pop(context);
                        appState.startQuiz(questions, timed: false);
                      },
                      child: const Text(
                        'Untimed Mode',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF3B82F6),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                      onPressed: () {
                        Navigator.pop(context);
                        appState.startQuiz(questions, timed: true);
                      },
                      child: const Text(
                        'Timed (30m)',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

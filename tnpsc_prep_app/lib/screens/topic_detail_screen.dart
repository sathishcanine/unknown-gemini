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

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = appState.isDarkMode;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);
    final mutedColor = isDark ? Colors.grey : const Color(0xFF64748B);
    final cardBg = isDark ? const Color(0xFF131A2A) : Colors.white;
    final scaffoldBg = isDark ? const Color(0xFF0B0F19) : const Color(0xFFF1F5F9);

    final subjectName = appState.activeSubject == 'Economy'
        ? 'Indian Economy'
        : appState.activeSubject == 'Polity'
            ? 'Indian Polity'
            : appState.activeSubject == 'Policy'
                ? 'Policy Notes'
                : appState.activeSubject == 'History'
                    ? 'Indian History'
                    : appState.activeSubject == 'INM'
                        ? 'Indian National Movement'
                        : appState.activeSubject == 'Chemistry'
                            ? 'Chemistry'
                            : 'Current Affairs';
    final topicName = appState.activeTopic ?? subjectName;

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
                      // 1. PYQs Card
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
                                onPressed: pyqList.isNotEmpty
                                    ? () => _showStartDialog(pyqList)
                                    : null,
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

                      // 2. Practice Batches
                      Text(
                        'Practice Batches (Textbook Generated)',
                        style: TextStyle(
                          fontFamily: 'Outfit',
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: textColor,
                        ),
                      ),
                      const SizedBox(height: 10),
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
                      else
                        ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: sortedBatchKeys.length,
                          itemBuilder: (context, index) {
                            final bKey = sortedBatchKeys[index];
                            final bQs = batchesMap[bKey]!;

                            return Card(
                              margin: const EdgeInsets.only(bottom: 12),
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
                                        color: Colors.purple.withOpacity(0.1),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Text('⚡', style: TextStyle(fontSize: 22)),
                                    ),
                                    const SizedBox(width: 16),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'Practice Batch $bKey',
                                            style: TextStyle(
                                              fontFamily: 'Outfit',
                                              fontSize: 15,
                                              fontWeight: FontWeight.bold,
                                              color: textColor,
                                            ),
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            '${bQs.length} Questions Available',
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
                                        backgroundColor: const Color(0xFF10B981),
                                        foregroundColor: Colors.white,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        elevation: 0,
                                      ),
                                      onPressed: () => _showStartDialog(bQs),
                                      child: const Text(
                                        'Start',
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
                            );
                          },
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

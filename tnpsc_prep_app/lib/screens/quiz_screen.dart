import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../models/question.dart';
import '../widgets/question_text.dart';
import '../services/api_service.dart';

class QuizScreen extends StatelessWidget {
  const QuizScreen({Key? key}) : super(key: key);

  @override
  Widget build(context) {
    final appState = Provider.of<AppState>(context);
    if (appState.quizQuestions.isEmpty) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(),
        ),
      );
    }

    final currentQuestion = appState.quizQuestions[appState.currentQuestionIndex];
    final isLast = appState.currentQuestionIndex == appState.quizQuestions.length - 1;

    // Format timer display
    String timerText = 'Learn Mode';
    if (appState.isTimed) {
      final mins = (appState.remainingSeconds ~/ 60).toString().padLeft(2, '0');
      final secs = (appState.remainingSeconds % 60).toString().padLeft(2, '0');
      timerText = '$mins:$secs';
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF131A2A),
        automaticallyImplyLeading: false,
        title: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
              icon: const Icon(Icons.close, color: Colors.white),
              onPressed: () => _showQuitConfirmation(context, appState),
            ),
            Expanded(
              child: Text(
                appState.activeTopic ?? 'Practice Quiz',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: appState.isTimed && appState.remainingSeconds < 300
                    ? const Color(0x33EF4444)
                    : const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: appState.isTimed && appState.remainingSeconds < 300
                      ? const Color(0xFFEF4444)
                      : Colors.transparent,
                ),
              ),
              child: Text(
                timerText,
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: appState.isTimed && appState.remainingSeconds < 300
                      ? const Color(0xFFEF4444)
                      : Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          // 1. Progress Bar
          Container(
            padding: const EdgeInsets.all(16.0),
            color: const Color(0xFF131A2A),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Question ${appState.currentQuestionIndex + 1} of ${appState.quizQuestions.length}',
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                    Text(
                      '${((appState.currentQuestionIndex + 1) / appState.quizQuestions.length * 100).round()}% Completed',
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: (appState.currentQuestionIndex + 1) / appState.quizQuestions.length,
                    backgroundColor: Colors.white.withOpacity(0.05),
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF3B82F6)),
                    minHeight: 6,
                  ),
                ),
              ],
            ),
          ),

          // 2. Question View (Scrollable)
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  // Monolingual for English / Tamil papers; bilingual for GS-style subjects.
                  if (appState.isTamilSection ||
                      appState.activeSubject == 'Tamil') ...[
                    _buildQuestionCard(
                      appState.displayQuestionText(currentQuestion),
                      'TA',
                      const Color(0xFF10B981),
                    ),
                  ] else ...[
                    _buildQuestionCard(
                      appState.displayQuestionText(currentQuestion),
                      'EN',
                      const Color(0xFF3B82F6),
                    ),
                    if (appState.showBilingualQuestions &&
                        currentQuestion.questionTa.isNotEmpty &&
                        currentQuestion.questionTa != currentQuestion.questionEn) ...[
                      const SizedBox(height: 16),
                      _buildQuestionCard(
                        currentQuestion.questionTa,
                        'TA',
                        const Color(0xFF10B981),
                      ),
                    ],
                  ],
                  if (currentQuestion.imageUrls.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    ...currentQuestion.imageUrls.map((url) {
                      final resolved = url.startsWith('http')
                          ? url
                          : '${ApiConfig.baseUrl}$url';
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(12),
                          child: Container(
                            width: double.infinity,
                            color: const Color(0xFF1E293B),
                            padding: const EdgeInsets.all(8),
                            child: Image.network(
                              resolved,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Padding(
                                padding: EdgeInsets.all(24),
                                child: Text(
                                  'Figure unavailable',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(color: Colors.grey),
                                ),
                              ),
                            ),
                          ),
                        ),
                      );
                    }),
                  ],
                  const SizedBox(height: 24),

                  // Option selections
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'Select Option:',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...currentQuestion.options.map((opt) {
                    final isSelected = appState.selectedAnswers[appState.currentQuestionIndex] == opt.key;
                    return _QuizOptionTile(
                      key: ValueKey('${appState.currentQuestionIndex}-${opt.key}'),
                      option: opt,
                      isSelected: isSelected,
                      question: currentQuestion,
                      appState: appState,
                    );
                  }).toList(),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        color: const Color(0xFF131A2A),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF1E293B),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 0,
              ),
              onPressed: appState.currentQuestionIndex > 0 ? () => appState.prevQuestion() : null,
              child: const Text(
                'Previous',
                style: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold),
              ),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: isLast ? const Color(0xFF10B981) : const Color(0xFF3B82F6),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 0,
              ),
              onPressed: () {
                if (isLast) {
                  appState.submitQuiz();
                } else {
                  appState.nextQuestion();
                }
              },
              child: Text(
                isLast ? 'Submit Test' : 'Next',
                style: const TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuestionCard(String text, String langCode, Color badgeColor) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF131A2A),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.04)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  langCode,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: badgeColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _parseHtmlQuestionText(text),
        ],
      ),
    );
  }

  Widget _parseHtmlQuestionText(String text) {
    // Replicates our clean match matching layouts row parser
    if (text.contains('match-container')) {
      final leftReg = RegExp(r"class=['\u0022]match-col-left['\u0022]>(.*?)<\/div>");
      final rightReg = RegExp(r"class=['\u0022]match-col-right['\u0022]>(.*?)<\/div>");
      
      final leftMatch = leftReg.firstMatch(text);
      final rightMatch = rightReg.firstMatch(text);
      
      String cleanTitle = text.split('<br>').first.replaceAll(RegExp(r'<[^>]*>'), '');
      String leftCol = leftMatch != null ? leftMatch.group(1)!.replaceAll('<br>', '\n') : '';
      String rightCol = rightMatch != null ? rightMatch.group(1)!.replaceAll('<br>', '\n') : '';
      
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            cleanTitle,
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  leftCol,
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 13,
                    height: 1.5,
                    color: Colors.white70,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  rightCol,
                  style: const TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 13,
                    height: 1.5,
                    color: Colors.white70,
                  ),
                ),
              ),
            ],
          ),
        ],
      );
    } else {
      return QuestionText(text);
    }
  }

  void _showQuitConfirmation(BuildContext context, AppState appState) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF0F172A),
          title: const Text(
            'Quit Practice?',
            style: TextStyle(fontFamily: 'Outfit', color: Colors.white),
          ),
          content: const Text(
            'Are you sure you want to end this practice session? Your progress will not be saved.',
            style: TextStyle(fontFamily: 'Inter', color: Colors.grey),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel', style: TextStyle(fontFamily: 'Inter', color: Colors.grey)),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                appState.quitQuiz();
              },
              child: const Text('Quit', style: TextStyle(fontFamily: 'Inter', color: Colors.red)),
            ),
          ],
        );
      },
    );
  }
}

class _QuizOptionTile extends StatefulWidget {
  final Option option;
  final bool isSelected;
  final Question question;
  final AppState appState;

  const _QuizOptionTile({
    Key? key,
    required this.option,
    required this.isSelected,
    required this.question,
    required this.appState,
  }) : super(key: key);

  @override
  State<_QuizOptionTile> createState() => _QuizOptionTileState();
}

class _QuizOptionTileState extends State<_QuizOptionTile>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scale;
  late final Animation<double> _shake;
  bool _wasShowingFeedback = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
    );
    _scale = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.06), weight: 35),
      TweenSequenceItem(tween: Tween(begin: 1.06, end: 0.97), weight: 30),
      TweenSequenceItem(tween: Tween(begin: 0.97, end: 1.0), weight: 35),
    ]).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

    _shake = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: -8.0), weight: 1),
      TweenSequenceItem(tween: Tween(begin: -8.0, end: 8.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 8.0, end: -5.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: -5.0, end: 5.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 5.0, end: 0.0), weight: 1),
    ]).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void didUpdateWidget(covariant _QuizOptionTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    final showFeedback = _shouldShowFeedback;
    if (showFeedback && !_wasShowingFeedback && (_isWrongSelection || _isCorrectReveal)) {
      _controller.forward(from: 0);
    }
    _wasShowingFeedback = showFeedback;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  bool get _isLearnMode => !widget.appState.isTimed;

  bool get _hasAnswered =>
      widget.appState.selectedAnswers.containsKey(widget.appState.currentQuestionIndex);

  bool get _shouldShowFeedback => _isLearnMode && _hasAnswered;

  bool get _isCorrectOption => widget.option.key == widget.question.correctOption;

  bool get _isWrongSelection =>
      _shouldShowFeedback && widget.isSelected && !_isCorrectOption;

  bool get _isCorrectReveal => _shouldShowFeedback && _isCorrectOption;

  @override
  Widget build(BuildContext context) {
    Color backgroundColor =
        widget.isSelected ? const Color(0x1F3B82F6) : const Color(0xFF131A2A);
    Color borderColor =
        widget.isSelected ? const Color(0xFF3B82F6) : Colors.white.withOpacity(0.04);
    Color badgeColor =
        widget.isSelected ? const Color(0xFF3B82F6) : const Color(0xFF1E293B);

    if (_isWrongSelection) {
      backgroundColor = const Color(0x33EF4444);
      borderColor = const Color(0xFFEF4444);
      badgeColor = const Color(0xFFEF4444);
    } else if (_isCorrectReveal) {
      backgroundColor = const Color(0x3310B981);
      borderColor = const Color(0xFF10B981);
      badgeColor = const Color(0xFF10B981);
    }

    final highlightActive = _isWrongSelection || _isCorrectReveal;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final dx = _isWrongSelection ? _shake.value : 0.0;
        final scale = highlightActive ? _scale.value : 1.0;
        return Transform.translate(
          offset: Offset(dx, 0),
          child: Transform.scale(
            scale: scale,
            child: child,
          ),
        );
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 380),
        curve: Curves.easeOutCubic,
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: borderColor,
            width: (widget.isSelected || highlightActive) ? 1.8 : 1.0,
          ),
          boxShadow: highlightActive
              ? [
                  BoxShadow(
                    color: (_isWrongSelection
                            ? const Color(0xFFEF4444)
                            : const Color(0xFF10B981))
                        .withOpacity(0.35),
                    blurRadius: 14,
                    spreadRadius: 0,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: ListTile(
          onTap: () => widget.appState.selectOption(widget.option.key),
          leading: AnimatedContainer(
            duration: const Duration(milliseconds: 380),
            curve: Curves.easeOutCubic,
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: badgeColor,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 280),
                switchInCurve: Curves.easeOutBack,
                switchOutCurve: Curves.easeIn,
                transitionBuilder: (child, animation) {
                  return ScaleTransition(
                    scale: animation,
                    child: FadeTransition(opacity: animation, child: child),
                  );
                },
                child: _isWrongSelection
                    ? const Icon(
                        Icons.close,
                        key: ValueKey('wrong'),
                        color: Colors.white,
                        size: 18,
                      )
                    : _isCorrectReveal
                        ? const Icon(
                            Icons.check,
                            key: ValueKey('correct'),
                            color: Colors.white,
                            size: 18,
                          )
                        : Text(
                            widget.option.key,
                            key: ValueKey('letter-${widget.option.key}'),
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: widget.isSelected ? Colors.white : Colors.grey,
                            ),
                          ),
              ),
            ),
          ),
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.appState.displayOptionText(widget.option),
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 13,
                  color: widget.isSelected || _isCorrectReveal
                      ? Colors.white
                      : Colors.white70,
                ),
              ),
              if (widget.appState.showBilingualQuestions &&
                  widget.option.textTa.isNotEmpty &&
                  widget.option.textTa != widget.option.textEn) ...[
                const SizedBox(height: 4),
                Text(
                  widget.option.textTa,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 12,
                    color: widget.isSelected || _isCorrectReveal
                        ? Colors.white60
                        : Colors.grey,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../models/question.dart';

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
    String timerText = 'Untimed';
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
                  // English Question Block
                  _buildQuestionCard(currentQuestion.questionEn, 'EN', const Color(0xFF3B82F6)),
                  const SizedBox(height: 16),
                  
                  // Tamil Question Block
                  if (currentQuestion.questionTa.isNotEmpty)
                    _buildQuestionCard(currentQuestion.questionTa, 'TA', const Color(0xFF10B981)),
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
                    return _buildOptionTile(opt, isSelected, appState);
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
      String clean = text.replaceAll('<br>', '\n').replaceAll(RegExp(r'<[^>]*>'), '');
      return Text(
        clean,
        style: const TextStyle(
          fontFamily: 'Inter',
          fontSize: 14,
          height: 1.4,
          color: Colors.white,
        ),
      );
    }
  }

  Widget _buildOptionTile(Option opt, bool isSelected, AppState appState) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: isSelected ? const Color(0x1F3B82F6) : const Color(0xFF131A2A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isSelected ? const Color(0xFF3B82F6) : Colors.white.withOpacity(0.04),
          width: isSelected ? 1.5 : 1.0,
        ),
      ),
      child: ListTile(
        onTap: () => appState.selectOption(opt.key),
        leading: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF3B82F6) : const Color(0xFF1E293B),
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(
              opt.key,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: isSelected ? Colors.white : Colors.grey,
              ),
            ),
          ),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              opt.textEn,
              style: TextStyle(
                fontFamily: 'Inter',
                fontSize: 13,
                color: isSelected ? Colors.white : Colors.white70,
              ),
            ),
            if (opt.textTa.isNotEmpty && opt.textTa != opt.textEn) ...[
              const SizedBox(height: 4),
              Text(
                opt.textTa,
                style: TextStyle(
                  fontFamily: 'Inter',
                  fontSize: 12,
                  color: isSelected ? Colors.white60 : Colors.grey,
                ),
              ),
            ],
          ],
        ),
      ),
    );
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

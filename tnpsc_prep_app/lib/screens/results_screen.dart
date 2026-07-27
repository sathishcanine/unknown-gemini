import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';

class ScoreRingPainter extends CustomPainter {
  final double scoreFraction;

  ScoreRingPainter(this.scoreFraction);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 6;

    final bgPaint = Paint()
      ..color = Colors.white.withOpacity(0.08)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8;

    final progressPaint = Paint()
      ..color = const Color(0xFF3B82F6)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, bgPaint);
    
    // Draw arc starting from top (-90 degrees)
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -1.5708, // -pi / 2
      scoreFraction * 6.28318, // fraction * 2 * pi
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(ScoreRingPainter oldDelegate) {
    return oldDelegate.scoreFraction != scoreFraction;
  }
}

class ResultsScreen extends StatelessWidget {
  const ResultsScreen({Key? key}) : super(key: key);

  @override
  Widget build(context) {
    final appState = Provider.of<AppState>(context);
    final session = appState.lastCompletedSession;

    if (session == null) {
      return const Scaffold(
        body: Center(
          child: Text('No test session found.'),
        ),
      );
    }

    final total = session.totalCount;
    final correct = session.correctCount;
    final incorrect = total - correct;
    final fraction = total > 0 ? (correct / total) : 0.0;
    final accuracy = (fraction * 100).round();

    // Format time taken
    final timeTaken = appState.timeTakenSeconds;
    final mins = timeTaken ~/ 60;
    final secs = timeTaken % 60;
    final timeStr = mins > 0 ? '${mins}m ${secs}s' : '${secs}s';

    String feedback = 'Good effort!';
    if (accuracy >= 90) {
      feedback = 'Outstanding performance! Keep it up!';
    } else if (accuracy >= 70) {
      feedback = 'Great job! You have strong understanding.';
    } else if (accuracy >= 50) {
      feedback = 'Passable, but needs revision. Review textbook references.';
    } else {
      feedback = 'Needs improvement. Recommend re-reading focus areas.';
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B0F19),
        elevation: 0,
        automaticallyImplyLeading: false,
        title: const Text(
          'Test Results',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 18,
            color: Colors.white,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.home, color: Colors.white),
            onPressed: () => appState.navigateToHome(),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Text(
              session.topic,
              style: const TextStyle(
                fontFamily: 'Outfit',
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.grey,
              ),
            ),
            const SizedBox(height: 16),

            // 1. Circular Progress Gauge
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF131A2A),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withOpacity(0.04)),
              ),
              child: Column(
                children: [
                  Center(
                    child: SizedBox(
                      width: 140,
                      height: 140,
                      child: CustomPaint(
                        painter: ScoreRingPainter(fraction),
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                '$correct/$total',
                                style: const TextStyle(
                                  fontFamily: 'Outfit',
                                  fontSize: 24,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '$accuracy% Acc',
                                style: const TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 11,
                                  color: Colors.grey,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    feedback,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 2. Metrics blocks
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: const Color(0x1110B981),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0x3310B981)),
                    ),
                    child: Column(
                      children: [
                        Text(
                          '$correct',
                          style: const TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF10B981),
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Correct',
                          style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: const Color(0x11EF4444),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0x33EF4444)),
                    ),
                    child: Column(
                      children: [
                        Text(
                          '$incorrect',
                          style: const TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFFEF4444),
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Incorrect',
                          style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    decoration: BoxDecoration(
                      color: const Color(0x113B82F6),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0x333B82F6)),
                    ),
                    child: Column(
                      children: [
                        Text(
                          timeStr,
                          style: const TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF3B82F6),
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Time Taken',
                          style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 28),

            // 3. Review Answers Title
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Review Answers',
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ),
            const SizedBox(height: 12),

            // 4. Scrollable Answers List
            ListView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: session.questions.length,
              itemBuilder: (context, index) {
                final q = session.questions[index];
                final selected = session.answers[index.toString()] ?? 'E';
                final isCorrect = selected == q.correctOption;

                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  color: const Color(0xFF131A2A),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side: BorderSide(color: Colors.white.withOpacity(0.04)),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'Question ${index + 1}',
                              style: const TextStyle(
                                fontFamily: 'Outfit',
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: Colors.grey,
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: isCorrect
                                    ? const Color(0x2210B981)
                                    : const Color(0x22EF4444),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                isCorrect ? 'Correct' : 'Incorrect',
                                style: TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                  color: isCorrect
                                      ? const Color(0xFF10B981)
                                      : const Color(0xFFEF4444),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Question content
                        Text(
                          q.questionEn.replaceAll('<br>', '\n').replaceAll(RegExp(r'<[^>]*>'), ''),
                          style: const TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 14,
                            color: Colors.white,
                          ),
                        ),
                        if (q.questionTa.isNotEmpty && q.questionTa != q.questionEn) ...[
                          const SizedBox(height: 8),
                          Text(
                            q.questionTa.replaceAll('<br>', '\n').replaceAll(RegExp(r'<[^>]*>'), ''),
                            style: const TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 13,
                              color: Colors.grey,
                            ),
                          ),
                        ],
                        const SizedBox(height: 16),

                        // Render selection indicators
                        _buildReviewOptionStatus('Your Answer: ($selected)', isCorrect ? Colors.green : Colors.red),
                        if (!isCorrect)
                          _buildReviewOptionStatus('Correct Answer: (${q.correctOption})', Colors.green),
                        
                        const SizedBox(height: 16),
                        const Divider(color: Colors.white10),
                        const SizedBox(height: 12),
                        
                        // Explanation
                        const Text(
                          'Explanation:',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF3B82F6),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          q.explanation,
                          style: const TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 13,
                            height: 1.4,
                            color: Colors.white70,
                          ),
                        ),
                        if (q.explanationTa.isNotEmpty && q.explanationTa != q.explanation) ...[
                          const SizedBox(height: 8),
                          Text(
                            q.explanationTa,
                            style: const TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 12,
                              height: 1.4,
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),

            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E293B),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: Colors.white10),
                  ),
                  elevation: 0,
                ),
                onPressed: () => appState.navigateToHome(),
                child: const Text(
                  'Back to Dashboard',
                  style: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewOptionStatus(String label, Color color) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontFamily: 'Inter',
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }
}

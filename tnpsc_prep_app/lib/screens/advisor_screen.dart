import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';

class AdvisorScreen extends StatelessWidget {
  const AdvisorScreen({Key? key}) : super(key: key);

  @override
  Widget build(context) {
    final appState = Provider.of<AppState>(context);
    final report = appState.weaknessReport;

    return Scaffold(
      backgroundColor: const Color(0xFF0B0F19),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0B0F19),
        elevation: 0,
        automaticallyImplyLeading: false,
        title: const Text(
          'AI Study Advisor',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 18,
            color: Colors.white,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Advisor Greeting Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF3B82F6), Color(0xFF1D4ED8)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  const Text(
                    '🤖',
                    style: TextStyle(fontSize: 40),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const [
                        Text(
                          'Personal AI Advisor',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'I analyze your practice history to pinpoint exactly which textbook chapters and pages you need to review to boost your TNPSC score.',
                          style: TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 12,
                            height: 1.4,
                            color: Colors.white70,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // 2. Diagnostic Content
            const Text(
              'Diagnostic Report',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 12),

            if (appState.totalTests == 0)
              _buildReportCard(
                '📚 No Data Collected Yet',
                'Start practicing batches or taking PYQ quizzes under any subject to unlock your personal weaknesses diagnostic report!',
                Colors.grey,
              )
            else if (report != null)
              Column(
                children: [
                  _buildReportCard(
                    '⚠️ Weakness Detected',
                    'Your accuracy on "${report['topic']}" is currently at ${report['accuracy']}%, which is below the target 70% threshold. Focus on the following resources:',
                    const Color(0xFFF59E0B),
                  ),
                  const SizedBox(height: 16),
                  if (report['textbook'] != null)
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: const Color(0xFF131A2A),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: Colors.white.withOpacity(0.04)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'RECOMMENDED STUDY SOURCE:',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF3B82F6),
                            ),
                          ),
                          const SizedBox(height: 12),
                          _buildDetailItem('Book Title', report['textbook']['book']),
                          _buildDetailItem('Chapter Name', report['textbook']['chapter']),
                          _buildDetailItem('Pages Scope', report['textbook']['pages']),
                          _buildDetailItem('Focus Area Notes', report['textbook']['focus']),
                        ],
                      ),
                    ),
                ],
              )
            else
              _buildReportCard(
                '✅ All Systems Clear!',
                'Outstanding! Your accuracy across all practiced topics is maintaining above the 70% threshold. Keep up the consistent work!',
                const Color(0xFF10B981),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildReportCard(String title, String message, Color color) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.2), width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontFamily: 'Outfit',
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 13,
              height: 1.4,
              color: Colors.white70,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailItem(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontFamily: 'Outfit',
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'Inter',
              fontSize: 13,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}

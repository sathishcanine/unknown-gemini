import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';

class PerformanceScreen extends StatefulWidget {
  const PerformanceScreen({Key? key}) : super(key: key);

  @override
  State<PerformanceScreen> createState() => _PerformanceScreenState();
}

class _PerformanceScreenState extends State<PerformanceScreen> {
  int? _openingSessionId;

  Future<void> _openSession(AppState appState, int sessionId) async {
    if (_openingSessionId != null) return;
    setState(() => _openingSessionId = sessionId);
    try {
      await appState.openSessionResults(sessionId);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open result: $e')),
      );
    } finally {
      if (mounted) setState(() => _openingSessionId = null);
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

    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        backgroundColor: scaffoldBg,
        elevation: 0,
        title: Text(
          'Performance Dashboard',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 20,
            color: textColor,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Mastery Analytics Summary Card
            Card(
              color: cardBg,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Overall Mastery',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: textColor,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _buildStatBox('Tests Solved', '${appState.totalTests}', Icons.assignment_turned_in, Colors.blue),
                        _buildStatBox('Avg Accuracy', '${appState.avgAccuracy}%', Icons.analytics, Colors.green),
                        _buildStatBox('Questions Done', '${appState.totalSolved}', Icons.help_outline, Colors.orange),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // 2. Recent Test Submissions (From PostgreSQL)
            Text(
              'Test Completion History',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: textColor,
              ),
            ),
            const SizedBox(height: 12),

            FutureBuilder<List<Map<String, dynamic>>>(
              future: ApiService().getUserHistory(appState.userEmail),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 40.0),
                      child: CircularProgressIndicator(),
                    ),
                  );
                }

                if (snapshot.hasError) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 40.0),
                      child: Text(
                        'Failed to load history from server.',
                        style: TextStyle(fontFamily: 'Inter', color: mutedColor),
                      ),
                    ),
                  );
                }

                final history = snapshot.data ?? [];
                if (history.isEmpty) {
                  return Card(
                    color: cardBg,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Center(
                        child: Column(
                          children: [
                            const Text(
                              '📝',
                              style: TextStyle(fontSize: 40),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No completed tests logged yet.',
                              style: TextStyle(
                                fontFamily: 'Outfit',
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: textColor,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Go to Home, select a subject, and start practicing!',
                              style: TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 12,
                                color: mutedColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }

                return ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: history.length,
                  itemBuilder: (context, index) {
                    final item = history[index];
                    final sessionId = item['id'] is int
                        ? item['id'] as int
                        : int.tryParse('${item['id']}') ?? 0;
                    final topic = item['topic_name'] ?? 'General studies practice';
                    final correct = item['correct_count'] ?? 0;
                    final total = item['total_count'] ?? 0;
                    final time = item['time_taken'] ?? 0;
                    final dateStr = item['timestamp'] ?? '';
                    final isOpening = _openingSessionId == sessionId;

                    String displayDate = 'Just now';
                    try {
                      if (dateStr.isNotEmpty) {
                        final parsed = DateTime.parse(dateStr).toLocal();
                        final year = parsed.year;
                        final month = parsed.month.toString().padLeft(2, '0');
                        final day = parsed.day.toString().padLeft(2, '0');
                        final hour = parsed.hour;
                        final minute = parsed.minute.toString().padLeft(2, '0');
                        final period = hour >= 12 ? 'PM' : 'AM';
                        final hour12 = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
                        displayDate = '$day/$month/$year • $hour12:$minute $period';
                      }
                    } catch (_) {}

                    final accuracy = total > 0 ? ((correct / total) * 100).round() : 0;

                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      color: cardBg,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                        side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
                      ),
                      child: ListTile(
                        onTap: sessionId > 0 && !isOpening
                            ? () => _openSession(appState, sessionId)
                            : null,
                        contentPadding: const EdgeInsets.all(16),
                        leading: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFF3B82F6).withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(
                            Icons.check_circle_outline,
                            color: Color(0xFF3B82F6),
                          ),
                        ),
                        title: Text(
                          topic,
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SizedBox(height: 4),
                            Text(
                              displayDate,
                              style: TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 11,
                                color: mutedColor,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Duration: ${time}s',
                              style: TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 11,
                                color: mutedColor,
                              ),
                            ),
                          ],
                        ),
                        trailing: isOpening
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                    decoration: BoxDecoration(
                                      color: accuracy >= 70
                                          ? const Color(0x2210B981)
                                          : const Color(0x22EF4444),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      '$correct/$total ($accuracy%)',
                                      style: TextStyle(
                                        fontFamily: 'Outfit',
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                        color: accuracy >= 70
                                            ? const Color(0xFF10B981)
                                            : const Color(0xFFEF4444),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Icon(Icons.chevron_right, color: mutedColor, size: 20),
                                ],
                              ),
                      ),
                    );
                  },
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatBox(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color, size: 20),
        ),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 11,
            color: Colors.grey,
          ),
        ),
      ],
    );
  }
}

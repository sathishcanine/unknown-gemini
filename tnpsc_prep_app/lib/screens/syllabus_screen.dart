import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';

class SyllabusScreen extends StatelessWidget {
  const SyllabusScreen({Key? key}) : super(key: key);

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
                : 'Current Affairs';

    return Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        backgroundColor: scaffoldBg,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back, color: textColor),
          onPressed: () => appState.navigateToHome(),
        ),
        title: Text(
          '$subjectName Syllabus',
          style: TextStyle(
            fontFamily: 'Outfit',
            fontWeight: FontWeight.bold,
            fontSize: 18,
            color: textColor,
          ),
        ),
      ),
      body: appState.loading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF3B82F6)),
              ),
            )
          : appState.syllabusList.isEmpty
              ? Center(
                  child: Text(
                    'No topics loaded for this subject.',
                    style: TextStyle(fontFamily: 'Inter', color: mutedColor),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: appState.syllabusList.length,
                  itemBuilder: (context, index) {
                    final item = appState.syllabusList[index];
                    final tName = item['name'] ?? '';
                    final tb = item['textbook'];

                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      color: cardBg,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                        side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
                      ),
                      child: ListTile(
                        contentPadding: const EdgeInsets.all(16),
                        leading: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFF3B82F6).withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(
                            Icons.assignment,
                            color: Color(0xFF3B82F6),
                          ),
                        ),
                        title: Text(
                          tName,
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: textColor,
                          ),
                        ),
                        subtitle: Text(
                          tb != null ? tb['book'].toString().split(' (').first : 'Bilingual syllabus topic module',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                        ),
                        trailing: Icon(Icons.arrow_forward_ios, size: 16, color: mutedColor),
                        onTap: () {
                          appState.selectTopic(tName);
                        },
                      ),
                    );
                  },
                ),
    );
  }
}

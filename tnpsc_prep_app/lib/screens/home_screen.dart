import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../services/api_service.dart';
import '../widgets/content_language_toggle.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _selectedCategory; // null, 'general_studies', 'current_affairs', 'pyqs'
  final ApiService _apiService = ApiService();

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = appState.isDarkMode;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);
    final mutedColor = isDark ? Colors.grey : const Color(0xFF64748B);
    final cardBg = isDark ? const Color(0xFF131A2A) : Colors.white;
    final scaffoldBg = isDark ? const Color(0xFF0B0F19) : const Color(0xFFF1F5F9);

    // Swipe/system back should leave a hub category before exiting the app.
    return PopScope(
      canPop: _selectedCategory == null,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && _selectedCategory != null) {
          setState(() => _selectedCategory = null);
        }
      },
      child: Scaffold(
      backgroundColor: scaffoldBg,
      appBar: AppBar(
        backgroundColor: scaffoldBg,
        elevation: 0,
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Image.asset(
                'assets/icon/app_icon.png',
                width: 36,
                height: 36,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Exam Aspirant',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                ),
                Text(
                  '${appState.activeGroup} Prep',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 12,
                    color: mutedColor,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          const ContentLanguageToggle(),
          IconButton(
            tooltip: 'Settings',
            onPressed: () => appState.navigateToProfile(),
            icon: Icon(
              Icons.settings_outlined,
              color: mutedColor,
            ),
          ),
          const SizedBox(width: 4),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await appState.fetchSubjects();
          await appState.syncStatsWithBackend();
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Weakness Highlight Banner (Dynamic)
              if (appState.weaknessReport != null)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0x22F59E0B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0x66F59E0B), width: 1.5),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '⚠️',
                        style: TextStyle(fontSize: 22),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Weakness Identified',
                              style: TextStyle(
                                fontFamily: 'Outfit',
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFFF59E0B),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'You score poorly on "${appState.weaknessReport!['topic']}" (${appState.weaknessReport!['accuracy']}% accuracy). Click review to view reference books.',
                              style: const TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 12,
                                color: Colors.white70,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      TextButton(
                        style: TextButton.styleFrom(
                          backgroundColor: const Color(0xFFF59E0B),
                          foregroundColor: Colors.black,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                        onPressed: () {
                          appState.selectSubject(appState.activeSubject ?? 'Economy');
                        },
                        child: const Text(
                          'Review',
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

              // 2. Analytics Progress Card
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark
                        ? [const Color(0xFF1E293B), const Color(0xFF0F172A)]
                        : [Colors.white, const Color(0xFFE2E8F0)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: isDark ? Colors.white.withOpacity(0.05) : Colors.black.withOpacity(0.05)),
                  boxShadow: [
                    BoxShadow(
                      color: isDark ? Colors.black.withOpacity(0.3) : Colors.black.withOpacity(0.05),
                      blurRadius: 15,
                      offset: const Offset(0, 10),
                    )
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                        Text(
                          '${appState.masteryPercent}%',
                          style: const TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF3B82F6),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: LinearProgressIndicator(
                        value: appState.masteryPercent / 100.0,
                        backgroundColor: isDark ? Colors.white.withOpacity(0.1) : Colors.black.withOpacity(0.05),
                        valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF3B82F6)),
                        minHeight: 8,
                      ),
                    ),
                    const SizedBox(height: 20),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        _buildStatItem('${appState.totalTests}', 'Tests Done', textColor, mutedColor),
                        _buildStatItem(
                          '${appState.totalCorrect}/${appState.totalSolved}',
                          'Correct answers',
                          textColor,
                          mutedColor,
                        ),
                        _buildStatItem('${appState.avgAccuracy}%', 'Avg Accuracy', textColor, mutedColor),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),

              // 3. Dynamic Category Render Block
              if (_selectedCategory == null)
                _buildMainMenuGrid(appState, isDark)
              else
                _buildCategoryListBlock(appState, isDark, textColor, cardBg, mutedColor),
            ],
          ),
        ),
      ),
      ),
    );
  }

  Widget _buildMainMenuGrid(AppState appState, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          appState.hubLabel('Preparation Hub'),
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.white : const Color(0xFF0F172A),
          ),
        ),
        const SizedBox(height: 14),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          mainAxisSpacing: 16,
          crossAxisSpacing: 16,
          childAspectRatio: 1.1,
          children: [
            _buildMenuCard(
              title: appState.hubLabel('General Studies'),
              icon: Icons.menu_book,
              color: const Color(0xFF3B82F6),
              isDark: isDark,
              onTap: () => setState(() => _selectedCategory = 'general_studies'),
            ),
            _buildMenuCard(
              title: appState.hubLabel('Tamil & English'),
              icon: Icons.translate,
              color: const Color(0xFF8B5CF6),
              isDark: isDark,
              onTap: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Language practice modules (Tamil & English) will be available in the next release!'),
                    duration: Duration(seconds: 3),
                  ),
                );
              },
            ),
            _buildMenuCard(
              title: appState.subjectDisplayName('Current Affairs').isNotEmpty
                  ? appState.subjectDisplayName('Current Affairs')
                  : appState.hubLabel('Current Affairs'),
              icon: Icons.newspaper,
              color: const Color(0xFFF59E0B),
              isDark: isDark,
              onTap: () => setState(() => _selectedCategory = 'current_affairs'),
            ),
            _buildMenuCard(
              title: appState.hubLabel('Past Year Questions'),
              icon: Icons.history_edu,
              color: const Color(0xFF10B981),
              isDark: isDark,
              onTap: () => setState(() => _selectedCategory = 'pyqs'),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _buildFullWidthMenuCard(
          title: appState.hubLabel('TVK-Government Policies'),
          subtitle: appState.hubLabel('Very Important'),
          imageAsset: 'assets/icon/tvk_government.png',
          accentColor: const Color(0xFFDC2626),
          isDark: isDark,
          onTap: () => appState.selectSubject('TVK'),
        ),
        const SizedBox(height: 12),
        _buildFullWidthMenuCard(
          title: appState.subjectDisplayName('CGS').isNotEmpty
              ? appState.subjectDisplayName('CGS')
              : appState.hubLabel('Central Government Schemes'),
          subtitle: appState.hubLabel('Union Schemes'),
          imageAsset: 'assets/icon/central_gov_schemes.png',
          accentColor: const Color(0xFFEA580C),
          isDark: isDark,
          onTap: () => appState.selectSubject('CGS'),
        ),
      ],
    );
  }

  Widget _buildFullWidthMenuCard({
    required String title,
    required String subtitle,
    required String imageAsset,
    required Color accentColor,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    final cardBg = isDark ? const Color(0xFF131A2A) : Colors.white;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);
    final mutedColor = isDark ? Colors.grey : const Color(0xFF64748B);

    return Card(
      color: cardBg,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: accentColor.withOpacity(0.35), width: 2),
                  boxShadow: [
                    BoxShadow(
                      color: accentColor.withOpacity(0.18),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: ClipOval(
                  child: Image.asset(
                    imageAsset,
                    fit: BoxFit.cover,
                    width: 56,
                    height: 56,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: textColor,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: accentColor,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios, size: 16, color: mutedColor),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMenuCard({
    required String title,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
    required bool isDark,
  }) {
    final cardBg = isDark ? const Color(0xFF131A2A) : Colors.white;
    final textColor = isDark ? Colors.white : const Color(0xFF0F172A);

    return Card(
      color: cardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14.0, horizontal: 12.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color.withOpacity(0.1),
                ),
                child: Icon(
                  icon,
                  size: 30,
                  color: color,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                title,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: 'Outfit',
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCategoryListBlock(AppState appState, bool isDark, Color textColor, Color cardBg, Color mutedColor) {
    String headerTitle = '';
    if (_selectedCategory == 'general_studies') {
      headerTitle = appState.hubLabel('General Studies');
    } else if (_selectedCategory == 'current_affairs') {
      headerTitle = appState.hubLabel('Current Affairs Batches');
    } else if (_selectedCategory == 'pyqs') {
      headerTitle = appState.hubLabel('Past Year Questions');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            IconButton(
              icon: Icon(Icons.arrow_back, color: textColor),
              onPressed: () => setState(() => _selectedCategory = null),
            ),
            const SizedBox(width: 8),
            Text(
              headerTitle,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: textColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (_selectedCategory == 'general_studies' || _selectedCategory == 'pyqs')
          _buildGeneralStudiesSubjects(appState, isDark, textColor, cardBg, mutedColor)
        else if (_selectedCategory == 'current_affairs')
          _buildCurrentAffairsBatches(appState, isDark, textColor, cardBg, mutedColor)
      ],
    );
  }

  Widget _buildGeneralStudiesSubjects(AppState appState, bool isDark, Color textColor, Color cardBg, Color mutedColor) {
    // Filter out Current Affairs, TVK, and CGS (TVK/CGS have their own home cards)
    final gsSubjects = appState.subjects
        .where((sub) =>
            sub['id'] != 'Current Affairs' &&
            sub['id'] != 'TVK' &&
            sub['id'] != 'CGS')
        .toList();

    if (gsSubjects.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: CircularProgressIndicator(),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: gsSubjects.length,
      itemBuilder: (context, index) {
        final sub = gsSubjects[index];
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
                color: isDark ? Colors.white.withOpacity(0.05) : Colors.black.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                sub['icon'],
                style: const TextStyle(fontSize: 22),
              ),
            ),
            title: Text(
              appState.subjectDisplayName(sub['id']?.toString()),
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: textColor,
              ),
            ),
            subtitle: Text(
              appState.questionsAvailableLabel(sub['questions_count']),
              style: TextStyle(
                fontFamily: 'Inter',
                fontSize: 12,
                color: mutedColor,
              ),
            ),
            trailing: Icon(Icons.arrow_forward_ios, size: 16, color: mutedColor),
            onTap: () {
              // Navigates directly to syllabus
              appState.selectSubject(sub['id']);
            },
          ),
        );
      },
    );
  }

  Widget _buildCurrentAffairsBatches(AppState appState, bool isDark, Color textColor, Color cardBg, Color mutedColor) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _apiService.getSyllabus('Current Affairs'),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(32.0),
              child: CircularProgressIndicator(),
            ),
          );
        }
        if (snapshot.hasError) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Text(
                'Failed to load batches: ${snapshot.error}',
                style: const TextStyle(color: Colors.red),
              ),
            ),
          );
        }

        final batches = snapshot.data ?? [];
        if (batches.isEmpty) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(32.0),
              child: Text(
                'No Current Affairs batches found.',
                style: TextStyle(color: Colors.grey),
              ),
            ),
          );
        }

        return ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: batches.length,
          itemBuilder: (context, index) {
            final batch = batches[index];
            final name = batch['name'] as String;
            final displayName = appState.topicDisplayNameFromItem(batch);
            final enShort = name.replaceAll('Current Affairs : ', '');
            final title = appState.isTamilContent
                ? displayName.replaceAll('நடப்பு நிகழ்வுகள் : ', '')
                : enShort;

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
                    color: const Color(0xFFF59E0B).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.calendar_month,
                    color: Color(0xFFF59E0B),
                  ),
                ),
                title: Text(
                  title,
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                ),
                subtitle: const Text(
                  'Bilingual monthly test bank',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
                trailing: Icon(Icons.arrow_forward_ios, size: 16, color: mutedColor),
                onTap: () {
                  // Direct navigation to TopicDetailScreen for this monthly batch
                  appState.selectCurrentAffairsTopic(name);
                },
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildStatItem(String value, String label, Color textColor, Color mutedColor) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontFamily: 'Outfit',
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: textColor,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontFamily: 'Inter',
            fontSize: 11,
            color: mutedColor,
          ),
        ),
      ],
    );
  }
}

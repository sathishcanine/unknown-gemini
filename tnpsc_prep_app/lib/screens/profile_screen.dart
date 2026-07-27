import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({Key? key}) : super(key: key);

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
          'Profile Settings',
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
            // 1. User Account Profile Card
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
                      width: 54,
                      height: 54,
                      decoration: BoxDecoration(
                        color: const Color(0xFF3B82F6).withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.person,
                          color: Color(0xFF3B82F6),
                          size: 28,
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Active Student',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: textColor,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            appState.userEmail,
                            style: TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 13,
                              color: mutedColor,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // 2. Settings Section Header
            Text(
              'App Settings',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF3B82F6),
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 12),

            // 3. Theme Toggle Tile
            Card(
              color: cardBg,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
              ),
              child: SwitchListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                secondary: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.wb_sunny, color: Colors.orange, size: 20),
                ),
                title: Text(
                  'Dark Theme Mode',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: textColor,
                  ),
                ),
                subtitle: const Text(
                  'Enable futuristic deep space dark mode styling',
                  style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                ),
                value: appState.isDarkMode,
                activeColor: const Color(0xFF3B82F6),
                onChanged: (bool val) {
                  appState.toggleTheme();
                },
              ),
            ),
            const SizedBox(height: 24),

            // 4. Account Management Section
            Text(
              'Account Management',
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: const Color(0xFFEF4444),
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 12),

            Card(
              color: cardBg,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: isDark ? Colors.white.withOpacity(0.04) : Colors.black.withOpacity(0.04)),
              ),
              child: Column(
                children: [
                  // Logout Button
                  ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.logout, color: Colors.orange, size: 20),
                    ),
                    title: Text(
                      'Logout Account',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: textColor,
                      ),
                    ),
                    subtitle: const Text(
                      'Safely sign out of this session on this device',
                      style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                    ),
                    trailing: Icon(Icons.chevron_right, color: mutedColor),
                    onTap: () async {
                      await appState.signOut();
                    },
                  ),
                  Divider(color: isDark ? Colors.white12 : Colors.black12, height: 1),
                  // Delete Account Button
                  ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.delete_forever, color: Colors.red, size: 20),
                    ),
                    title: const Text(
                      'Delete My Account',
                      style: TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: Colors.red,
                      ),
                    ),
                    subtitle: const Text(
                      'Permanently erase all test progress, history, and user profile data from servers',
                      style: TextStyle(fontFamily: 'Inter', fontSize: 11, color: Colors.grey),
                    ),
                    trailing: const Icon(Icons.chevron_right, color: Colors.red),
                    onTap: () {
                      _showDeleteConfirmationDialog(context, appState);
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showDeleteConfirmationDialog(BuildContext context, AppState appState) {
    showDialog(
      context: context,
      builder: (BuildContext dialogContext) {
        final isDark = appState.isDarkMode;
        final dialogBg = isDark ? const Color(0xFF131A2A) : Colors.white;
        final txtColor = isDark ? Colors.white : const Color(0xFF0F172A);

        return AlertDialog(
          backgroundColor: dialogBg,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(
            '⚠️ Permanent Account Deletion?',
            style: TextStyle(
              fontFamily: 'Outfit',
              fontWeight: FontWeight.bold,
              color: txtColor,
              fontSize: 18,
            ),
          ),
          content: Text(
            'This action is irreversible. Deleting your account will completely wipe your user records, practice test histories, and scores from our PostgreSQL database. Are you sure you want to proceed?',
            style: TextStyle(
              fontFamily: 'Inter',
              color: isDark ? Colors.white70 : Colors.black87,
              fontSize: 14,
              height: 1.4,
            ),
          ),
          actions: [
            TextButton(
              child: const Text(
                'Cancel',
                style: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold),
              ),
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              onPressed: () async {
                Navigator.of(dialogContext).pop();
                // Execute deletion
                await appState.deleteUserAccount();
              },
              child: const Text(
                'Delete Permanently',
                style: TextStyle(fontFamily: 'Outfit', fontWeight: FontWeight.bold),
              ),
            ),
          ],
        );
      },
    );
  }
}

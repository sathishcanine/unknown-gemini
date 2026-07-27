import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../services/update_service.dart';

/// Update prompt shown when Firebase Remote Config reports a newer build is
/// available. Force updates block dismissal (no back button, no "Later").
class UpdateDialog extends StatelessWidget {
  final UpdateInfo info;
  final bool isDarkMode;

  const UpdateDialog({
    Key? key,
    required this.info,
    required this.isDarkMode,
  }) : super(key: key);

  static Future<void> show(
    BuildContext context,
    UpdateInfo info, {
    required bool isDarkMode,
  }) {
    final isForce = info.severity == UpdateSeverity.force;
    return showDialog(
      context: context,
      barrierDismissible: !isForce,
      builder: (ctx) => PopScope(
        canPop: !isForce,
        child: UpdateDialog(info: info, isDarkMode: isDarkMode),
      ),
    );
  }

  Future<void> _openStore(BuildContext context) async {
    final uri = Uri.parse(info.updateUrl);
    try {
      final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!launched) throw Exception('Could not launch $uri');
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open update link: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isForce = info.severity == UpdateSeverity.force;
    final cardColor = isDarkMode ? const Color(0xFF131A2A) : Colors.white;
    final textColor = isDarkMode ? Colors.white : const Color(0xFF0F172A);
    final subTextColor = isDarkMode ? Colors.grey[400] : const Color(0xFF64748B);
    const accentColor = Color(0xFF3B82F6);

    return Dialog(
      backgroundColor: cardColor,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      insetPadding: const EdgeInsets.symmetric(horizontal: 32),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 28, 24, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: accentColor.withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.system_update_rounded,
                color: accentColor,
                size: 32,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              info.title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: textColor,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              info.message,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: subTextColor, height: 1.45),
            ),
            if (info.latestVersionName.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'Latest version: ${info.latestVersionName}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: accentColor,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: () => _openStore(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: accentColor,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text(
                  'Update Now',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ),
            ),
            if (!isForce) ...[
              const SizedBox(height: 4),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text('Later', style: TextStyle(color: subTextColor)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

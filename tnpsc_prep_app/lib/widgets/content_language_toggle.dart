import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';

/// Compact EN / தமிழ் control. Shows the language you can switch to.
class ContentLanguageToggle extends StatelessWidget {
  const ContentLanguageToggle({Key? key, this.compact = true}) : super(key: key);

  final bool compact;

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);
    final isDark = appState.isDarkMode;
    final label = appState.isTamilContent ? 'English' : 'தமிழ்';

    return Padding(
      padding: EdgeInsets.only(right: compact ? 8 : 0),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => appState.toggleContentLanguage(),
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: EdgeInsets.symmetric(
              horizontal: compact ? 12 : 14,
              vertical: compact ? 6 : 8,
            ),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: const Color(0xFF3B82F6).withOpacity(0.55),
              ),
              color: isDark
                  ? const Color(0xFF3B82F6).withOpacity(0.12)
                  : const Color(0xFF3B82F6).withOpacity(0.08),
            ),
            child: Text(
              label,
              style: TextStyle(
                fontFamily: 'Outfit',
                fontSize: compact ? 13 : 14,
                fontWeight: FontWeight.w700,
                color: const Color(0xFF3B82F6),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

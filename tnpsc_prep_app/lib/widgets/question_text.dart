import 'package:flutter/material.dart';

/// Renders quiz/results question text with light HTML support:
/// - `<br>` → newline
/// - `<u>…</u>` → underlined (TNPSC "underlined word" stems)
/// - other tags stripped
class QuestionText extends StatelessWidget {
  const QuestionText(
    this.text, {
    Key? key,
    this.style = const TextStyle(
      fontFamily: 'Inter',
      fontSize: 14,
      height: 1.4,
      color: Colors.white,
    ),
  }) : super(key: key);

  final String text;
  final TextStyle style;

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(children: _spans(text, style)),
      style: style,
    );
  }

  static List<InlineSpan> _spans(String raw, TextStyle base) {
    final normalized = raw.replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n');
    final re = RegExp(r'<u>(.*?)</u>', caseSensitive: false, dotAll: true);
    final spans = <InlineSpan>[];
    var start = 0;
    for (final m in re.allMatches(normalized)) {
      if (m.start > start) {
        spans.add(TextSpan(text: _stripTags(normalized.substring(start, m.start))));
      }
      spans.add(
        TextSpan(
          text: _stripTags(m.group(1) ?? ''),
          style: base.copyWith(
            decoration: TextDecoration.underline,
            decorationColor: base.color ?? Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
      );
      start = m.end;
    }
    if (start < normalized.length) {
      spans.add(TextSpan(text: _stripTags(normalized.substring(start))));
    }
    if (spans.isEmpty) {
      spans.add(TextSpan(text: _stripTags(normalized)));
    }
    return spans;
  }

  static String _stripTags(String s) => s.replaceAll(RegExp(r'<[^>]*>'), '');
}

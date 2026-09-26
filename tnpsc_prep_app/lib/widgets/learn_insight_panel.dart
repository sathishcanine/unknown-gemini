import 'package:flutter/material.dart';

import '../models/question.dart';
import '../providers/app_state.dart';

/// Learn Mode learning area: Why / Tip / Trick / Remember chips.
/// Auto-scrolls into view so users never miss it.
class LearnInsightPanel extends StatefulWidget {
  final Question question;
  final AppState appState;
  final String? selectedKey;
  final bool isCorrect;
  final VoidCallback? onAppeared;

  const LearnInsightPanel({
    super.key,
    required this.question,
    required this.appState,
    required this.selectedKey,
    required this.isCorrect,
    this.onAppeared,
  });

  @override
  State<LearnInsightPanel> createState() => _LearnInsightPanelState();
}

class _LearnInsightPanelState extends State<LearnInsightPanel>
    with TickerProviderStateMixin {
  late final AnimationController _enter;
  late final AnimationController _pulse;
  late final Animation<double> _fade;
  late final Animation<Offset> _slide;
  late final Animation<double> _glow;

  @override
  void initState() {
    super.initState();
    _enter = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 480),
    );
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _fade = CurvedAnimation(parent: _enter, curve: Curves.easeOutCubic);
    _slide = Tween<Offset>(
      begin: const Offset(0, 0.12),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _enter, curve: Curves.easeOutCubic));
    _glow = Tween<double>(begin: 0.22, end: 0.55).animate(
      CurvedAnimation(parent: _pulse, curve: Curves.easeInOut),
    );

    _enter.forward();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      widget.onAppeared?.call();
    });
  }

  @override
  void dispose() {
    _enter.dispose();
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final card = _LearnCardContent.fromQuestion(
      widget.question,
      widget.appState,
    );
    if (card.isEmpty) return const SizedBox.shrink();

    final accent = widget.isCorrect
        ? const Color(0xFF10B981)
        : const Color(0xFFF59E0B);

    return FadeTransition(
      opacity: _fade,
      child: SlideTransition(
        position: _slide,
        child: AnimatedBuilder(
          animation: _glow,
          builder: (context, child) {
            return Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 12, bottom: 20),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    const Color(0xFF0F172A),
                    Color.lerp(const Color(0xFF111827), accent, 0.12)!,
                  ],
                ),
                border: Border.all(
                  color: accent.withValues(alpha: _glow.value),
                  width: 1.6,
                ),
                boxShadow: [
                  BoxShadow(
                    color: accent.withValues(alpha: 0.28 * _glow.value),
                    blurRadius: 22,
                    spreadRadius: 1,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: child,
            );
          },
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Header(
                isCorrect: widget.isCorrect,
                correctKey: widget.question.correctOption,
                accent: accent,
              ),
              if (card.rememberChips.isNotEmpty)
                _RememberStrip(chips: card.rememberChips, accent: accent),
              if (card.why.isNotEmpty)
                _SectionCard(
                  icon: Icons.menu_book_rounded,
                  label: 'WHY',
                  accent: const Color(0xFF60A5FA),
                  child: _BoldBody(text: card.why),
                ),
              if (card.tip.isNotEmpty)
                _SectionCard(
                  icon: Icons.tips_and_updates_rounded,
                  label: 'TIP',
                  accent: const Color(0xFF34D399),
                  child: _BoldBody(text: card.tip, emphasizeAll: true),
                ),
              if (card.trick.isNotEmpty)
                _SectionCard(
                  icon: Icons.bolt_rounded,
                  label: 'EXAM TRICK',
                  accent: const Color(0xFFFBBF24),
                  child: _BoldBody(text: card.trick, emphasizeAll: true),
                ),
              if (card.whyTa.isNotEmpty)
                _SectionCard(
                  icon: Icons.translate_rounded,
                  label: 'தமிழ்',
                  accent: const Color(0xFFA78BFA),
                  child: Text(
                    card.whyTa,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 12.5,
                      height: 1.45,
                      color: Colors.white.withValues(alpha: 0.78),
                    ),
                  ),
                ),
              const SizedBox(height: 10),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final bool isCorrect;
  final String correctKey;
  final Color accent;

  const _Header({
    required this.isCorrect,
    required this.correctKey,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  accent.withValues(alpha: 0.35),
                  accent.withValues(alpha: 0.12),
                ],
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              isCorrect ? Icons.workspace_premium_rounded : Icons.school_rounded,
              color: accent,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isCorrect ? 'Learning boost' : 'Learning area',
                  style: const TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  isCorrect
                      ? 'Lock this in before Next'
                      : 'Correct · $correctKey  ·  scroll tips below',
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    color: Colors.white.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: accent.withValues(alpha: 0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.auto_awesome, size: 13, color: accent),
                const SizedBox(width: 4),
                Text(
                  'LEARN',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                    color: accent,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _RememberStrip extends StatelessWidget {
  final List<String> chips;
  final Color accent;

  const _RememberStrip({required this.chips, required this.accent});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 2, 12, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 8),
            child: Row(
              children: [
                Icon(Icons.psychology_alt_rounded,
                    size: 14, color: accent.withValues(alpha: 0.9)),
                const SizedBox(width: 6),
                Text(
                  'REMEMBER',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.2,
                    color: accent,
                  ),
                ),
              ],
            ),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: chips
                .take(5)
                .map(
                  (c) => Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: accent.withValues(alpha: 0.35),
                      ),
                    ),
                    child: Text(
                      c,
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color accent;
  final Widget child;

  const _SectionCard({
    required this.icon,
    required this.label,
    required this.accent,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: accent.withValues(alpha: 0.28)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Icon(icon, size: 16, color: accent),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.15,
                      color: accent,
                    ),
                  ),
                  const SizedBox(height: 6),
                  child,
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Bold years, acronyms, quoted names, and key numeric facts.
class _BoldBody extends StatelessWidget {
  final String text;
  final bool emphasizeAll;

  const _BoldBody({required this.text, this.emphasizeAll = false});

  static final _pattern = RegExp(
    r'''(?:"[^"]{2,40}"|'[^']{2,40}'|\b\d{3,4}(?:[–\-]\d{2,4})?\b|\b[A-Z]{2,}(?:[/\-][A-Z]{2,})*\b|\b\d+(?:\.\d+)?%?\b)''',
  );

  @override
  Widget build(BuildContext context) {
    final base = TextStyle(
      fontFamily: 'Inter',
      fontSize: emphasizeAll ? 13.5 : 13,
      height: 1.5,
      color: Colors.white.withValues(alpha: 0.92),
      fontWeight: emphasizeAll ? FontWeight.w600 : FontWeight.w500,
    );
    final bold = base.copyWith(
      fontWeight: FontWeight.w800,
      color: Colors.white,
    );

    final spans = <TextSpan>[];
    var start = 0;
    for (final m in _pattern.allMatches(text)) {
      if (m.start > start) {
        spans.add(TextSpan(text: text.substring(start, m.start), style: base));
      }
      spans.add(TextSpan(text: m.group(0), style: bold));
      start = m.end;
    }
    if (start < text.length) {
      spans.add(TextSpan(text: text.substring(start), style: base));
    }

    return Text.rich(TextSpan(children: spans));
  }
}

class _LearnCardContent {
  final String why;
  final String whyTa;
  final String tip;
  final String trick;
  final List<String> rememberChips;

  const _LearnCardContent({
    required this.why,
    required this.whyTa,
    required this.tip,
    required this.trick,
    required this.rememberChips,
  });

  bool get isEmpty =>
      why.isEmpty && tip.isEmpty && trick.isEmpty && rememberChips.isEmpty;

  factory _LearnCardContent.fromQuestion(Question q, AppState appState) {
    final why = appState.displayExplanationText(q).trim();
    var tip = appState.displayLearningTip(q).trim();
    var trick = appState.displayExamTrick(q).trim();

    // Bilingual TA why only when EN is primary and TA differs.
    var whyTa = '';
    if (appState.showBilingualQuestions &&
        !(appState.activeSubject == 'Tamil' || appState.isTamilSection)) {
      final ta = q.explanationTa.trim();
      if (ta.isNotEmpty && ta != why && ta != q.explanation.trim()) {
        whyTa = ta;
      }
    }

    final chips = _extractRememberChips(why.isNotEmpty ? why : q.explanation);
    if (tip.isEmpty && why.isNotEmpty) {
      tip = _synthesizeTip(why, chips);
    }
    if (trick.isEmpty && why.isNotEmpty) {
      trick = _synthesizeTrick(why, chips, q.correctOption);
    }

    return _LearnCardContent(
      why: why,
      whyTa: whyTa,
      tip: tip,
      trick: trick,
      rememberChips: chips,
    );
  }
}

List<String> _extractRememberChips(String text) {
  if (text.trim().isEmpty) return const [];
  final out = <String>[];
  final seen = <String>{};

  void add(String s) {
    final t = s.trim();
    if (t.length < 2 || t.length > 42) return;
    final key = t.toLowerCase();
    if (seen.add(key)) out.add(t);
  }

  for (final m in RegExp(r'"([^"]{2,40})"').allMatches(text)) {
    add(m.group(1)!);
  }
  for (final m in RegExp(r'\(([A-Z]{2,}(?:[/\-][A-Z]{2,})*)\)').allMatches(text)) {
    add(m.group(1)!);
  }
  for (final m in RegExp(r'\b\d{3,4}(?:[–\-]\d{2,4})?\b').allMatches(text)) {
    add(m.group(0)!);
  }
  for (final m in RegExp(r'\b[A-Z]{2,}(?:[/\-][A-Z]{2,})*\b').allMatches(text)) {
    final a = m.group(0)!;
    if (a != 'EN' && a != 'TA' && a != 'THE' && a != 'AND' && a != 'FOR') {
      add(a);
    }
  }

  // Pull a short program / scheme name before "was launched" / "is called"
  final name = RegExp(
    r'([A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){1,5})\s+(?:\(.*?\)\s+)?'
    r'(?:was|is|were|are)\s+(?:launched|called|known|introduced)',
  ).firstMatch(text);
  if (name != null) add(name.group(1)!);

  return out.take(5).toList();
}

String _synthesizeTip(String why, List<String> chips) {
  if (chips.isNotEmpty) {
    final lead = chips.take(2).join(' · ');
    return 'Link $lead to this question type — same pattern repeats in PYQs.';
  }
  final first = why.split(RegExp(r'[.!?]')).first.trim();
  if (first.length > 12 && first.length < 110) {
    return first;
  }
  return 'Read the year + scheme name together — TNPSC loves that pair.';
}

String _synthesizeTrick(String why, List<String> chips, String correct) {
  final year = chips.where((c) => RegExp(r'^\d{3,4}').hasMatch(c)).toList();
  final acronyms =
      chips.where((c) => RegExp(r'^[A-Z]{2,}').hasMatch(c)).toList();
  if (year.isNotEmpty && acronyms.isNotEmpty) {
    return 'Eliminate options that miss ${year.first} or ${acronyms.first}.';
  }
  if (acronyms.isNotEmpty) {
    return 'Spot ${acronyms.first} in the stem → lock option $correct.';
  }
  if (year.isNotEmpty) {
    return 'Match the year ${year.first} — wrong era options are traps.';
  }
  return 'Cut look-alike revolutions/schemes first, then pick $correct.';
}

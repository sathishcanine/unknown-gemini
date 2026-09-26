import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../services/razorpay_checkout.dart';

class _Quote {
  const _Quote({required this.en, required this.ta});
  final String en;
  final String ta;
}

const _quotes = <_Quote>[
  _Quote(
    en: 'ஒரு முடிவு — உன் வாழ்க்கையை மாற்றும்.',
    ta: 'கனவு காண். முயற்சி செய். வெற்றி பெறு.',
  ),
  _Quote(
    en: 'உன்னில் முதலீடு செய் — வெற்றி உனக்கே.',
    ta: 'கஷ்டம் இன்று. கெளரவம் நாளை.',
  ),
  _Quote(
    en: 'TNPSC கனவு — இன்றே தொடங்கு.',
    ta: 'நீயே உன் ஹீரோ. படி. போராடு. வெல்.',
  ),
];

class PremiumScreen extends StatefulWidget {
  const PremiumScreen({super.key});

  @override
  State<PremiumScreen> createState() => _PremiumScreenState();
}

class _PremiumScreenState extends State<PremiumScreen>
    with TickerProviderStateMixin {
  int _quoteIndex = 0;
  Timer? _quoteTimer;
  String? _selectedCode;
  bool _loading = true;
  List<Map<String, dynamic>> _plans = const [];

  late final AnimationController _enterCtrl;
  late final AnimationController _shimmerCtrl;
  late final AnimationController _pulseCtrl;

  static const _gold = Color(0xFFF0C674);
  static const _ink = Color(0xFF050A12);
  static const _panel = Color(0xFF0C1420);

  static const _fallbackPlans = <Map<String, dynamic>>[
    {
      'code': '2m',
      'name': '2 Months',
      'name_ta': '2 மாதங்கள்',
      'duration_days': 60,
      'price_inr': 99,
      'default_price_inr': 99,
      'has_override': false,
    },
    {
      'code': '1y',
      'name': '1 Year',
      'name_ta': '1 வருடம்',
      'duration_days': 365,
      'price_inr': 249,
      'default_price_inr': 249,
      'has_override': false,
    },
  ];

  @override
  void initState() {
    super.initState();
    _enterCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..forward();
    _shimmerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    )..repeat();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat(reverse: true);

    _quoteTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted) return;
      setState(() => _quoteIndex = (_quoteIndex + 1) % _quotes.length);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPlans());
  }

  bool _paying = false;
  RazorpayCheckout? _checkout;

  @override
  void dispose() {
    _quoteTimer?.cancel();
    _checkout?.dispose();
    _enterCtrl.dispose();
    _shimmerCtrl.dispose();
    _pulseCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadPlans() async {
    final appState = Provider.of<AppState>(context, listen: false);
    try {
      final plans = await appState.fetchSubscriptionPlans();
      if (!mounted) return;
      // Drop retired 1-month plan even if an older API still returns it.
      final filtered = plans
          .where((p) => p['code']?.toString() != '1m')
          .toList(growable: false);
      setState(() {
        _plans = filtered.isNotEmpty ? filtered : _fallbackPlans;
        final codes = _plans.map((p) => p['code']?.toString()).toSet();
        if (_selectedCode == null || !codes.contains(_selectedCode)) {
          _selectedCode = _plans.first['code']?.toString() ?? '2m';
        }
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _plans = _fallbackPlans;
        _selectedCode ??= '2m';
        _loading = false;
      });
    }
  }

  Map<String, dynamic>? get _selectedPlan {
    for (final p in _plans) {
      if (p['code']?.toString() == _selectedCode) return p;
    }
    return _plans.isEmpty ? null : _plans.first;
  }

  int _priceOf(Map<String, dynamic> p) {
    final v = p['price_inr'] ?? p['default_price_inr'] ?? 0;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? 0;
  }

  int _defaultPriceOf(Map<String, dynamic> p) {
    final v = p['default_price_inr'] ?? p['price_inr'] ?? 0;
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? 0;
  }

  String _saveLabel(Map<String, dynamic> p) {
    final days = (p['duration_days'] as num?)?.toInt() ?? 30;
    final months = math.max(1, (days / 30).round());
    final per = (_priceOf(p) / months).round();
    return '₹$per / month';
  }

  Future<void> _onContinue() async {
    if (_paying) return;
    HapticFeedback.mediumImpact();
    final plan = _selectedPlan;
    if (plan == null) return;
    final code = plan['code']?.toString();
    if (code == null || code.isEmpty) return;

    final appState = Provider.of<AppState>(context, listen: false);
    if (appState.userEmail.isEmpty || !appState.isAuthenticated) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please sign in to continue.')),
      );
      return;
    }

    setState(() => _paying = true);
    _checkout?.dispose();
    _checkout = RazorpayCheckout(
      userId: appState.userEmail,
      planCode: code,
      onSuccess: (entitlement) async {
        await appState.applyEntitlement(entitlement);
        if (!mounted) return;
        setState(() => _paying = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Payment successful — Premium unlocked!'),
            behavior: SnackBarBehavior.floating,
          ),
        );
        appState.navigateBackFromPremium();
      },
      onFailure: (message) {
        if (!mounted) return;
        setState(() => _paying = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            behavior: SnackBarBehavior.floating,
          ),
        );
      },
    );
    await _checkout!.start();
    // Keep _paying true until Razorpay success/failure callbacks fire.
  }

  @override
  Widget build(BuildContext context) {
    final quote = _quotes[_quoteIndex];
    final selected = _selectedPlan;
    final bottomPad = MediaQuery.paddingOf(context).bottom;
    final topPad = MediaQuery.paddingOf(context).top;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: _ink,
        body: Stack(
          children: [
            // Full atmospheric background
            Positioned.fill(
              child: Image.asset(
                'assets/images/premium_quote_bg.png',
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topRight,
                      end: Alignment.bottomLeft,
                      colors: [Color(0xFF16324A), _ink],
                    ),
                  ),
                ),
              ),
            ),
            // Depth overlays
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Colors.black.withValues(alpha: 0.25),
                      _ink.withValues(alpha: 0.55),
                      _ink,
                    ],
                    stops: const [0.0, 0.38, 0.72],
                  ),
                ),
              ),
            ),
            // Soft gold glow orb
            Positioned(
              top: -40,
              right: -60,
              child: AnimatedBuilder(
                animation: _pulseCtrl,
                builder: (_, __) {
                  final t = 0.55 + (_pulseCtrl.value * 0.25);
                  return Container(
                    width: 220,
                    height: 220,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _gold.withValues(alpha: 0.22 * t),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),

            CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(24, topPad + 56, 24, 20),
                    child: FadeTransition(
                      opacity: CurvedAnimation(
                        parent: _enterCtrl,
                        curve: const Interval(0.0, 0.55, curve: Curves.easeOut),
                      ),
                      child: SlideTransition(
                        position: Tween<Offset>(
                          begin: const Offset(0, 0.08),
                          end: Offset.zero,
                        ).animate(CurvedAnimation(
                          parent: _enterCtrl,
                          curve: const Interval(0.0, 0.55, curve: Curves.easeOutCubic),
                        )),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'வெற்றி உனக்கு\nசொந்தம்',
                              style: TextStyle(
                                fontFamily: 'Outfit',
                                fontSize: 26,
                                height: 1.25,
                                fontWeight: FontWeight.w800,
                                color: Colors.white.withValues(alpha: 0.96),
                                letterSpacing: 0.1,
                              ),
                            ),
                            const SizedBox(height: 12),
                            AnimatedSwitcher(
                              duration: const Duration(milliseconds: 600),
                              switchInCurve: Curves.easeOut,
                              switchOutCurve: Curves.easeIn,
                              transitionBuilder: (child, anim) {
                                return FadeTransition(
                                  opacity: anim,
                                  child: SlideTransition(
                                    position: Tween<Offset>(
                                      begin: const Offset(0, 0.12),
                                      end: Offset.zero,
                                    ).animate(anim),
                                    child: child,
                                  ),
                                );
                              },
                              child: Column(
                                key: ValueKey(_quoteIndex),
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Container(
                                    width: 24,
                                    height: 2.5,
                                    margin: const EdgeInsets.only(bottom: 10),
                                    decoration: BoxDecoration(
                                      color: _gold,
                                      borderRadius: BorderRadius.circular(999),
                                    ),
                                  ),
                                  Text(
                                    quote.en,
                                    style: const TextStyle(
                                      fontFamily: 'Outfit',
                                      fontSize: 16,
                                      height: 1.4,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.white,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    quote.ta,
                                    style: TextStyle(
                                      fontFamily: 'Inter',
                                      fontSize: 13,
                                      height: 1.4,
                                      fontWeight: FontWeight.w500,
                                      color: const Color(0xFFF0C674).withValues(alpha: 0.9),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: List.generate(_quotes.length, (i) {
                                final active = i == _quoteIndex;
                                return AnimatedContainer(
                                  duration: const Duration(milliseconds: 280),
                                  margin: const EdgeInsets.only(right: 7),
                                  width: active ? 22 : 7,
                                  height: 7,
                                  decoration: BoxDecoration(
                                    color: active ? _gold : Colors.white24,
                                    borderRadius: BorderRadius.circular(999),
                                  ),
                                );
                              }),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                SliverToBoxAdapter(
                  child: FadeTransition(
                    opacity: CurvedAnimation(
                      parent: _enterCtrl,
                      curve: const Interval(0.25, 0.85, curve: Curves.easeOut),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(18, 0, 18, 130),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _AiCoachHero(pulse: _pulseCtrl),
                          const SizedBox(height: 14),
                          const _BenefitGrid(),
                          const SizedBox(height: 28),
                          Row(
                            children: [
                              const Text(
                                'Pick a plan',
                                style: TextStyle(
                                  fontFamily: 'Outfit',
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                'Cancel anytime',
                                style: TextStyle(
                                  fontFamily: 'Inter',
                                  fontSize: 11,
                                  color: Colors.white.withValues(alpha: 0.45),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          if (_loading)
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 36),
                              child: Center(
                                child: CircularProgressIndicator(color: _gold),
                              ),
                            )
                          else
                            ...List.generate(_plans.length, (i) {
                              final p = _plans[i];
                              final code = p['code']?.toString() ?? '';
                              return Padding(
                                padding: EdgeInsets.only(bottom: i == _plans.length - 1 ? 0 : 10),
                                child: _PlanRow(
                                  plan: p,
                                  selected: code == _selectedCode,
                                  price: _priceOf(p),
                                  defaultPrice: _defaultPriceOf(p),
                                  subtitle: _saveLabel(p),
                                  badge: code == '1y'
                                      ? 'BEST VALUE'
                                      : code == '2m'
                                          ? 'POPULAR'
                                          : null,
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    setState(() => _selectedCode = code);
                                  },
                                ),
                              );
                            }),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),

            Positioned(
              top: topPad + 10,
              left: 14,
              child: _GlassIconButton(
                icon: Icons.close_rounded,
                onTap: () =>
                    Provider.of<AppState>(context, listen: false).navigateBackFromPremium(),
              ),
            ),

            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _CheckoutDock(
                plan: selected,
                price: selected == null ? 0 : _priceOf(selected),
                bottomPad: bottomPad,
                shimmer: _shimmerCtrl,
                paying: _paying,
                onContinue: _onContinue,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AiCoachHero extends StatelessWidget {
  const _AiCoachHero({required this.pulse});
  final AnimationController pulse;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: pulse,
      builder: (_, __) {
        final glow = 0.12 + pulse.value * 0.1;
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: const LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF1A1408), Color(0xFF0E1A28), Color(0xFF12241F)],
            ),
            border: Border.all(color: const Color(0xFFF0C674).withValues(alpha: 0.55), width: 1.2),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFF0C674).withValues(alpha: glow),
                blurRadius: 28,
                spreadRadius: 1,
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFFF0C674).withValues(alpha: 0.35),
                      const Color(0xFFF0C674).withValues(alpha: 0.08),
                    ],
                  ),
                ),
                child: const Icon(Icons.auto_awesome_rounded, color: Color(0xFFF0C674), size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Text(
                          'AI Coach',
                          style: TextStyle(
                            fontFamily: 'Outfit',
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFFF0C674),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF0C674),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: const Text(
                            'HIGHLIGHT',
                            style: TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.8,
                              color: Color(0xFF1A1208),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'A personal coach that finds weak topics and builds your path to rank.',
                      style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12.5,
                        height: 1.4,
                        color: Colors.white.withValues(alpha: 0.72),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _BenefitGrid extends StatelessWidget {
  const _BenefitGrid();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        _BenefitBanner(
          title: 'TVK Policies',
          subtitle: 'Schemes & policy focus',
          imageAsset: 'assets/icon/tvk_government.png',
          imageFit: BoxFit.cover,
          imageAlignment: Alignment(0, -0.2),
        ),
        SizedBox(height: 10),
        _BenefitBanner(
          title: 'Current Affairs',
          subtitle: 'Exam-ready daily drills',
          imageAsset: 'assets/images/current_affairs.png',
          imageFit: BoxFit.cover,
          imageAlignment: Alignment.center,
        ),
        SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: _BenefitMiniTile(
                title: 'Oneline Notes',
                subtitle: 'Last-minute recall',
                imageAsset: 'assets/images/oneline_notes_tile.png',
              ),
            ),
            SizedBox(width: 10),
            Expanded(
              child: _BenefitMiniTile(
                title: 'Mock Tests',
                subtitle: 'Unlimited full access',
                imageAsset: 'assets/images/mock_tests_tile.png',
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _BenefitBanner extends StatelessWidget {
  const _BenefitBanner({
    required this.title,
    required this.subtitle,
    required this.imageAsset,
    this.imageFit = BoxFit.cover,
    this.imageAlignment = Alignment.center,
  });

  final String title;
  final String subtitle;
  final String imageAsset;
  final BoxFit imageFit;
  final Alignment imageAlignment;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 92,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.28),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Row(
              children: [
                SizedBox(
                  width: 108,
                  child: Image.asset(
                    imageAsset,
                    fit: imageFit,
                    alignment: imageAlignment,
                    width: 108,
                    height: 92,
                  ),
                ),
                Expanded(
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Color(0xFF101820), Color(0xFF0A1018)],
                      ),
                    ),
                  ),
                ),
              ],
            ),
            // Soft blend from photo into panel
            Positioned(
              left: 70,
              top: 0,
              bottom: 0,
              width: 56,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      Colors.transparent,
                      const Color(0xFF0A1018).withValues(alpha: 0.95),
                    ],
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(118, 0, 14, 0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        color: Colors.white.withValues(alpha: 0.62),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BenefitMiniTile extends StatelessWidget {
  const _BenefitMiniTile({
    required this.title,
    required this.subtitle,
    required this.imageAsset,
  });

  final String title;
  final String subtitle;
  final String imageAsset;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 118,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset(imageAsset, fit: BoxFit.cover),
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.black.withValues(alpha: 0.1),
                    Colors.black.withValues(alpha: 0.78),
                  ],
                ),
              ),
            ),
            Positioned(
              left: 12,
              right: 12,
              bottom: 12,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11,
                      color: Colors.white.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlanRow extends StatelessWidget {
  const _PlanRow({
    required this.plan,
    required this.selected,
    required this.price,
    required this.defaultPrice,
    required this.subtitle,
    required this.onTap,
    this.badge,
  });

  final Map<String, dynamic> plan;
  final bool selected;
  final int price;
  final int defaultPrice;
  final String subtitle;
  final String? badge;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hasDiscount = price < defaultPrice;
    final name = plan['name']?.toString() ?? '';
    final nameTa = plan['name_ta']?.toString();

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: selected
              ? const LinearGradient(
                  colors: [Color(0xFF2A2112), Color(0xFF132030)],
                )
              : null,
          color: selected ? null : Colors.white.withValues(alpha: 0.045),
          border: Border.all(
            color: selected
                ? const Color(0xFFF0C674)
                : Colors.white.withValues(alpha: 0.1),
            width: selected ? 1.6 : 1,
          ),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: const Color(0xFFF0C674).withValues(alpha: 0.18),
                    blurRadius: 18,
                    offset: const Offset(0, 8),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: selected ? const Color(0xFFF0C674) : Colors.white38,
                  width: 2,
                ),
                color: selected ? const Color(0xFFF0C674) : Colors.transparent,
              ),
              child: selected
                  ? const Icon(Icons.check_rounded, size: 14, color: Color(0xFF1A1208))
                  : null,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          fontFamily: 'Outfit',
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      if (badge != null) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF0C674),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            badge!,
                            style: const TextStyle(
                              fontFamily: 'Outfit',
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                              color: Color(0xFF1A1208),
                              letterSpacing: 0.4,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(
                    [
                      if (nameTa != null && nameTa.isNotEmpty) nameTa,
                      subtitle,
                    ].join(' · '),
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11.5,
                      color: Colors.white.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '₹$price',
                  style: TextStyle(
                    fontFamily: 'Outfit',
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: selected ? const Color(0xFFF0C674) : Colors.white,
                  ),
                ),
                if (hasDiscount)
                  Text(
                    '₹$defaultPrice',
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11,
                      decoration: TextDecoration.lineThrough,
                      color: Colors.white.withValues(alpha: 0.4),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CheckoutDock extends StatelessWidget {
  const _CheckoutDock({
    required this.plan,
    required this.price,
    required this.bottomPad,
    required this.shimmer,
    required this.onContinue,
    this.paying = false,
  });

  final Map<String, dynamic>? plan;
  final int price;
  final double bottomPad;
  final AnimationController shimmer;
  final VoidCallback onContinue;
  final bool paying;

  @override
  Widget build(BuildContext context) {
    final name = plan?['name']?.toString() ?? 'Premium';
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
        child: Container(
          padding: EdgeInsets.fromLTRB(16, 14, 16, 14 + bottomPad),
          decoration: BoxDecoration(
            color: const Color(0xFF050A12).withValues(alpha: 0.82),
            border: Border(
              top: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '₹$price',
                      style: const TextStyle(
                        fontFamily: 'Outfit',
                        fontSize: 26,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      name,
                      style: TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        color: Colors.white.withValues(alpha: 0.55),
                      ),
                    ),
                  ],
                ),
              ),
              AnimatedBuilder(
                animation: shimmer,
                builder: (_, __) {
                  return Container(
                    height: 54,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      gradient: LinearGradient(
                        begin: Alignment(-1.2 + shimmer.value * 2.4, 0),
                        end: Alignment(0.2 + shimmer.value * 2.4, 0),
                        colors: const [
                          Color(0xFFC9953A),
                          Color(0xFFF0C674),
                          Color(0xFFFFE2A8),
                          Color(0xFFF0C674),
                          Color(0xFFC9953A),
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFFF0C674).withValues(alpha: 0.35),
                          blurRadius: 16,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(16),
                        onTap: paying ? null : onContinue,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 26),
                          child: Center(
                            child: Text(
                              paying ? 'Opening…' : 'Continue',
                              style: const TextStyle(
                                fontFamily: 'Outfit',
                                fontWeight: FontWeight.w800,
                                fontSize: 16,
                                color: Color(0xFF1A1208),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GlassIconButton extends StatelessWidget {
  const _GlassIconButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ClipOval(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Material(
          color: Colors.white.withValues(alpha: 0.12),
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Icon(icon, color: Colors.white, size: 20),
            ),
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';

class WhatsAppPhoneScreen extends StatefulWidget {
  const WhatsAppPhoneScreen({Key? key}) : super(key: key);

  @override
  State<WhatsAppPhoneScreen> createState() => _WhatsAppPhoneScreenState();
}

class _WhatsAppPhoneScreenState extends State<WhatsAppPhoneScreen> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  String? _error;
  bool _saving = false;

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  bool _isValidIndianMobile(String raw) {
    return RegExp(r'^[6-9]\d{9}$').hasMatch(raw);
  }

  Future<void> _submit(AppState appState, {required bool skip}) async {
    if (_saving) return;

    if (!skip) {
      final digits = _controller.text.trim();
      if (!_isValidIndianMobile(digits)) {
        setState(() {
          _error = 'Enter a valid 10-digit WhatsApp number';
        });
        return;
      }
      setState(() {
        _error = null;
        _saving = true;
      });
      try {
        await appState.saveWhatsAppNumber(digits);
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Could not save number: $e')),
          );
        }
      } finally {
        if (mounted) setState(() => _saving = false);
      }
      return;
    }

    setState(() => _saving = true);
    try {
      await appState.skipWhatsAppNumber();
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final appState = Provider.of<AppState>(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/whatsapp_phone_bg.png',
            fit: BoxFit.cover,
          ),
          // Readability veil — keeps form legible over the art
          DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  const Color(0xFF070B14).withOpacity(0.55),
                  const Color(0xFF070B14).withOpacity(0.72),
                  const Color(0xFF070B14).withOpacity(0.92),
                ],
                stops: const [0.0, 0.45, 1.0],
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(28, 8, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerRight,
                    child: Transform.scale(
                      scale: 0.64,
                      alignment: Alignment.centerRight,
                      child: IconButton(
                        onPressed: _saving ? null : () => _submit(appState, skip: true),
                        tooltip: 'Close',
                        style: IconButton.styleFrom(
                          backgroundColor: Colors.white.withOpacity(0.08),
                          foregroundColor: Colors.white.withOpacity(0.85),
                        ),
                        icon: const Icon(Icons.close_rounded, size: 22),
                      ),
                    ),
                  ),
                  // Spacers shrink when the keyboard opens (avoids overflow).
                  // Do not branch layout on keyboard state — that dismisses the IME.
                  const Spacer(flex: 2),
                  Center(
                    child: Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: const Color(0xFF25D366).withOpacity(0.16),
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: const Color(0xFF25D366).withOpacity(0.35),
                        ),
                      ),
                      child: const Icon(
                        Icons.chat_rounded,
                        color: Color(0xFF25D366),
                        size: 30,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  const Text(
                    'Stay exam-ready\non WhatsApp',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 30,
                      height: 1.15,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: -0.3,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Get batch reminders, syllabus tips, and important TNPSC updates — straight to your WhatsApp.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 14,
                      height: 1.5,
                      color: Colors.white.withOpacity(0.72),
                    ),
                  ),
                  const Spacer(flex: 2),
                  Text(
                    'WhatsApp number',
                    style: TextStyle(
                      fontFamily: 'Outfit',
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Colors.white.withOpacity(0.85),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF131A2A).withOpacity(0.88),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: _error != null
                            ? Colors.redAccent.withOpacity(0.7)
                            : Colors.white.withOpacity(0.08),
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    child: Row(
                      children: [
                        Text(
                          '+91',
                          style: TextStyle(
                            fontFamily: 'Inter',
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                            color: Colors.white.withOpacity(0.9),
                          ),
                        ),
                        Container(
                          margin: const EdgeInsets.symmetric(horizontal: 12),
                          width: 1,
                          height: 22,
                          color: Colors.white.withOpacity(0.12),
                        ),
                        Expanded(
                          child: TextField(
                            controller: _controller,
                            focusNode: _focusNode,
                            keyboardType: TextInputType.phone,
                            style: const TextStyle(
                              fontFamily: 'Inter',
                              fontSize: 16,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                              letterSpacing: 0.8,
                            ),
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly,
                              LengthLimitingTextInputFormatter(10),
                            ],
                            decoration: InputDecoration(
                              hintText: '10-digit mobile number',
                              hintStyle: TextStyle(
                                fontFamily: 'Inter',
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: Colors.white.withOpacity(0.35),
                                letterSpacing: 0,
                              ),
                              border: InputBorder.none,
                              contentPadding:
                                  const EdgeInsets.symmetric(vertical: 18),
                            ),
                            onChanged: (_) {
                              if (_error != null) setState(() => _error = null);
                            },
                            onSubmitted: (_) => _submit(appState, skip: false),
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _error!,
                      style: const TextStyle(
                        fontFamily: 'Inter',
                        fontSize: 12,
                        color: Colors.redAccent,
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  SizedBox(
                    height: 52,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF25D366),
                        foregroundColor: const Color(0xFF06351A),
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      onPressed: _saving ? null : () => _submit(appState, skip: false),
                      child: _saving
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.4,
                                valueColor:
                                    AlwaysStoppedAnimation(Color(0xFF06351A)),
                              ),
                            )
                          : const Text(
                              'Continue',
                              style: TextStyle(
                                fontFamily: 'Outfit',
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Used only for study updates. No spam.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: 'Inter',
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.4),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

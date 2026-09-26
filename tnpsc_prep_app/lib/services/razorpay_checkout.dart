import 'package:flutter/foundation.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';

import 'api_service.dart';

typedef PaymentSuccessCallback = void Function(Map<String, dynamic> entitlement);
typedef PaymentFailureCallback = void Function(String message);

/// Opens Razorpay checkout for a plan. Verify signature on backend before unlocking.
class RazorpayCheckout {
  RazorpayCheckout({
    required this.userId,
    required this.planCode,
    required this.onSuccess,
    required this.onFailure,
  });

  final String userId;
  final String planCode;
  final PaymentSuccessCallback onSuccess;
  final PaymentFailureCallback onFailure;

  final _api = ApiService();
  Razorpay? _razorpay;
  bool _busy = false;

  Future<void> start() async {
    if (_busy) return;
    _busy = true;
    try {
      final order = await _api.createRazorpayOrder(
        userId: userId,
        planCode: planCode,
      );
      if (order == null) {
        onFailure('Could not create payment order. Check Razorpay keys on server.');
        return;
      }
      if (order['_error'] != null) {
        onFailure(order['_error'].toString());
        return;
      }

      _razorpay?.clear();
      _razorpay = Razorpay();
      _razorpay!.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handleSuccess);
      _razorpay!.on(Razorpay.EVENT_PAYMENT_ERROR, _handleError);
      _razorpay!.on(Razorpay.EVENT_EXTERNAL_WALLET, (_) {});

      final prefill = order['prefill'];
      final options = <String, dynamic>{
        'key': order['key_id'],
        'amount': order['amount'],
        'currency': order['currency'] ?? 'INR',
        'name': 'ACE TNPSC Unlimited',
        'description': order['plan_name'] ?? 'Premium',
        'order_id': order['order_id'],
        'prefill': <String, dynamic>{
          'email': (prefill is Map ? prefill['email'] : null) ??
              (userId.contains('@') ? userId : ''),
        },
        'theme': {'color': '#C9953A'},
        'method': {
          'upi': true,
          'card': false,
          'netbanking': false,
          'wallet': false,
        },
      };

      _razorpay!.open(options);
    } catch (e) {
      onFailure(e.toString());
    } finally {
      _busy = false;
    }
  }

  Future<void> _handleSuccess(PaymentSuccessResponse response) async {
    try {
      final entitlement = await _api.verifyRazorpayPayment(
        userId: userId,
        orderId: response.orderId ?? '',
        paymentId: response.paymentId ?? '',
        signature: response.signature ?? '',
      );
      if (entitlement != null) {
        onSuccess(entitlement);
      } else {
        onFailure('Payment received but verification failed. Contact support with payment ID.');
      }
    } catch (e) {
      onFailure('Verification error: $e');
    } finally {
      dispose();
    }
  }

  void _handleError(PaymentFailureResponse response) {
    final msg = response.message?.toString() ?? 'Payment cancelled or failed';
    debugPrint('Razorpay error: $msg code=${response.code}');
    onFailure(msg);
    dispose();
  }

  void dispose() {
    _razorpay?.clear();
    _razorpay = null;
  }
}

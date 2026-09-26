"""Razorpay order create / signature verify helpers.

Env:
  RAZORPAY_KEY_ID
  RAZORPAY_KEY_SECRET
  RAZORPAY_WEBHOOK_SECRET (optional; falls back to KEY_SECRET)
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, Optional

import requests

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"


def razorpay_configured() -> bool:
    return bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET"))


def razorpay_key_id() -> str:
    return os.getenv("RAZORPAY_KEY_ID", "")


def _auth():
    return (os.getenv("RAZORPAY_KEY_ID", ""), os.getenv("RAZORPAY_KEY_SECRET", ""))


def create_order(amount_paise: int, receipt: str, notes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not razorpay_configured():
        raise RuntimeError("Razorpay keys not configured")
    if amount_paise < 100:
        raise ValueError("amount must be at least 100 paise (₹1)")
    payload = {
        "amount": int(amount_paise),
        "currency": "INR",
        "receipt": receipt[:40],
        "notes": notes or {},
        "payment_capture": 1,
    }
    res = requests.post(RAZORPAY_ORDERS_URL, auth=_auth(), json=payload, timeout=20)
    if res.status_code >= 300:
        raise RuntimeError(f"Razorpay order failed: {res.status_code} {res.text}")
    return res.json()


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    if not secret or not order_id or not payment_id or not signature:
        return False
    body = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET") or os.getenv("RAZORPAY_KEY_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

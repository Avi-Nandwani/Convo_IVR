# app/utils/security.py
"""
Webhook signing / verification helpers.

Provides:
 - sign_payload(payload_bytes, secret) -> signature (hex)
 - verify_signature(payload_bytes, signature, secret) -> bool

We use HMAC-SHA256 and hex encoding. Many providers use a timestamp + signature scheme;
you can extend these helpers as needed.
"""
import hmac
import hashlib
from typing import Union, Optional
from app.config import get_settings

settings = get_settings()


def sign_payload(payload: Union[bytes, str], secret: Optional[str] = None) -> str:
    """
    Return hex HMAC-SHA256 signature for payload.
    """
    if secret is None:
        secret = settings.WEBHOOK_SECRET or ""
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    key = secret.encode("utf-8")
    sig = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return sig


def verify_signature(payload: Union[bytes, str], signature: str, secret: Optional[str] = None) -> bool:
    """
    Verify signature (hex string) for payload. Uses constant-time compare.
    """
    if secret is None:
        secret = settings.WEBHOOK_SECRET or ""
    expected = sign_payload(payload, secret)
    # Constant-time compare
    return hmac.compare_digest(expected, signature)

from __future__ import annotations
import base64
import hashlib
import json
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _fernet() -> Fernet:
    # Derive a stable encryption key from a backend-only secret. Production deployments
    # should set INTEGRATION_SECRET_KEY to a long random value independent of source code.
    material = (settings.integration_secret_key or settings.jwt_secret_key).encode('utf-8')
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_secret_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    return _fernet().encrypt(raw).decode('utf-8')


def decrypt_secret_payload(ciphertext: str | None) -> dict:
    if not ciphertext:
        return {}
    try:
        raw = _fernet().decrypt(ciphertext.encode('utf-8'))
        value = json.loads(raw.decode('utf-8'))
        return value if isinstance(value, dict) else {}
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return {}


def hint(value: str | None, visible: int = 3) -> str | None:
    if not value:
        return None
    text = str(value)
    if len(text) <= visible:
        return '•' * len(text)
    return text[:visible] + '•' * max(4, min(10, len(text) - visible))

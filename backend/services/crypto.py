"""Token encryption for OAuth credentials."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from backend.config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    key = settings.token_encryption_key
    if not key:
        # Dev fallback — derive from app secret (not for production)
        import base64
        import hashlib

        derived = base64.urlsafe_b64encode(hashlib.sha256(settings.app_secret_key.encode()).digest())
        return Fernet(derived)
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_json(data: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict[str, Any]:
    try:
        return json.loads(_fernet().decrypt(token.encode()).decode())
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted token") from exc

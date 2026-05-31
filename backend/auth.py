"""Auth helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.models import User
from backend.db.session import get_db

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _sign(data: bytes) -> str:
    return hmac.new(settings.app_secret_key.encode(), data, hashlib.sha256).hexdigest()


def create_session_token(user_id: int) -> str:
    payload = {
        "uid": user_id,
        "exp": int(time.time()) + settings.session_lifetime_hours * 3600,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(raw).decode()
    sig = _sign(raw)
    return f"{b64}.{sig}"


def decode_session_token(token: str) -> int | None:
    try:
        b64, sig = token.rsplit(".", 1)
        raw = base64.urlsafe_b64decode(b64.encode())
        if not hmac.compare_digest(_sign(raw), sig):
            return None
        payload = json.loads(raw.decode())
        if payload.get("exp", 0) < time.time():
            return None
        return int(payload["uid"])
    except Exception:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_session_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get("session")
    if not token:
        return None
    user_id = decode_session_token(token)
    if not user_id:
        return None
    return db.get(User, user_id)

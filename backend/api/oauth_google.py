"""Google / YouTube OAuth."""

from __future__ import annotations

import json
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import get_settings
from backend.db.models import ConnectedAccount, User
from backend.db.session import get_db
from backend.services.crypto import encrypt_json

router = APIRouter(prefix="/api/oauth/google", tags=["oauth"])
settings = get_settings()

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "openid",
    "email",
    "profile",
]

_oauth_states: dict[str, int] = {}


@router.get("/connect")
def google_connect(user: User = Depends(get_current_user)):
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID not configured")
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = user.id
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = _oauth_states.pop(state, None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    with httpx.Client(timeout=30) as client:
        token_resp = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=token_resp.text)
        data = token_resp.json()
        refresh_token = data.get("refresh_token")
        access_token = data.get("access_token")

        profile_resp = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        label = profile_resp.json().get("email", "YouTube") if profile_resp.status_code == 200 else "YouTube"

    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token — revoke app access and reconnect")

    tokens = {"refresh_token": refresh_token, "access_token": access_token}
    existing = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id, ConnectedAccount.provider == "google")
        .first()
    )
    if existing:
        existing.encrypted_tokens = encrypt_json(tokens)
        existing.account_label = label
        existing.status = "connected"
    else:
        db.add(
            ConnectedAccount(
                user_id=user_id,
                provider="google",
                account_label=label,
                encrypted_tokens=encrypt_json(tokens),
                status="connected",
            )
        )
    db.commit()
    return RedirectResponse(f"{settings.app_url}/settings?connected=google")

"""Meta (Facebook) OAuth."""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import get_settings
from backend.db.models import ConnectedAccount, User
from backend.db.session import get_db
from backend.services.crypto import encrypt_json

router = APIRouter(prefix="/api/oauth/meta", tags=["oauth"])
settings = get_settings()

META_SCOPES = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "instagram_basic",
    "instagram_content_publish",
    "business_management",
]

_oauth_states: dict[str, int] = {}


@router.get("/connect")
def meta_connect(user: User = Depends(get_current_user)):
    if not settings.meta_app_id:
        raise HTTPException(status_code=400, detail="META_APP_ID not configured")
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = user.id
    params = {
        "client_id": settings.meta_app_id,
        "redirect_uri": settings.meta_redirect_uri,
        "scope": ",".join(META_SCOPES),
        "state": state,
        "response_type": "code",
    }
    url = f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
def meta_callback(code: str, state: str, db: Session = Depends(get_db)):
    user_id = _oauth_states.pop(state, None)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    with httpx.Client(timeout=30) as client:
        token_resp = client.get(
            f"https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": settings.meta_redirect_uri,
                "code": code,
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail=token_resp.text)
        access_token = token_resp.json().get("access_token")

        # Long-lived token
        ll_resp = client.get(
            f"https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": access_token,
            },
        )
        if ll_resp.status_code == 200:
            access_token = ll_resp.json().get("access_token", access_token)

        pages_resp = client.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": access_token},
        )
        pages = pages_resp.json().get("data", [])
        page_id = settings.facebook_page_id
        page_token = access_token
        ig_id = settings.instagram_business_account_id
        label = "Meta Account"

        if pages:
            page = pages[0]
            page_id = page.get("id", page_id)
            page_token = page.get("access_token", access_token)
            label = page.get("name", label)
            ig_resp = client.get(
                f"https://graph.facebook.com/v21.0/{page_id}",
                params={"fields": "instagram_business_account", "access_token": page_token},
            )
            ig_data = ig_resp.json().get("instagram_business_account")
            if ig_data:
                ig_id = ig_data.get("id", ig_id)

        perms_resp = client.get(
            "https://graph.facebook.com/v21.0/me/permissions",
            params={"access_token": page_token},
        )
        permissions = {
            p["permission"]: p["status"]
            for p in perms_resp.json().get("data", [])
            if p.get("status") == "granted"
        }

    tokens = {
        "access_token": page_token,
        "facebook_page_id": page_id,
        "instagram_business_account_id": ig_id,
    }
    existing = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id, ConnectedAccount.provider == "meta")
        .first()
    )
    import json

    if existing:
        existing.encrypted_tokens = encrypt_json(tokens)
        existing.permissions_json = json.dumps(permissions)
        existing.account_label = label
        existing.status = "connected"
    else:
        db.add(
            ConnectedAccount(
                user_id=user_id,
                provider="meta",
                account_label=label,
                encrypted_tokens=encrypt_json(tokens),
                permissions_json=json.dumps(permissions),
                status="connected",
            )
        )
    db.commit()
    return RedirectResponse(f"{settings.app_url}/settings?connected=meta")

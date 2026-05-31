"""Connected accounts status."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import get_settings
from backend.db.models import ConnectedAccount, User
from backend.db.session import get_db
from backend.schemas import AccountStatus

router = APIRouter(prefix="/api/accounts", tags=["accounts"])
settings = get_settings()

REQUIRED_META = {"pages_manage_posts", "instagram_content_publish", "instagram_basic"}


@router.get("", response_model=list[AccountStatus])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results: list[AccountStatus] = []
    for provider in ("meta", "google"):
        acct = (
            db.query(ConnectedAccount)
            .filter(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == provider)
            .first()
        )
        if acct:
            perms = json.loads(acct.permissions_json) if acct.permissions_json else {}
            missing = [p for p in REQUIRED_META if p not in perms] if provider == "meta" else []
            status = "connected" if not missing else "missing_permissions"
            results.append(
                AccountStatus(
                    provider=provider,
                    connected=True,
                    status=status,
                    account_label=acct.account_label,
                    permissions=perms,
                    missing_permissions=missing,
                )
            )
        else:
            # Env fallback
            if provider == "meta" and settings.instagram_graph_access_token:
                results.append(
                    AccountStatus(
                        provider="meta",
                        connected=True,
                        status="env_fallback",
                        account_label="Environment credentials",
                    )
                )
            elif provider == "google":
                results.append(
                    AccountStatus(provider="google", connected=False, status="disconnected")
                )
            else:
                results.append(
                    AccountStatus(provider=provider, connected=False, status="disconnected")
                )
    return results


@router.post("/{provider}/test")
def test_connection(provider: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import httpx

    if provider == "meta":
        token = settings.instagram_graph_access_token
        ig_id = settings.instagram_business_account_id
        acct = (
            db.query(ConnectedAccount)
            .filter(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == "meta")
            .first()
        )
        if acct:
            from backend.services.crypto import decrypt_json

            t = decrypt_json(acct.encrypted_tokens)
            token = t.get("access_token", token)
            ig_id = t.get("instagram_business_account_id", ig_id)
        if not token or not ig_id:
            return {"ok": False, "error": "Not connected"}
        resp = httpx.get(
            f"https://graph.facebook.com/v21.0/{ig_id}",
            params={"fields": "username", "access_token": token},
            timeout=15,
        )
        return {"ok": resp.status_code == 200, "data": resp.json() if resp.status_code == 200 else resp.text}
    return {"ok": False, "error": "Test not implemented for provider"}

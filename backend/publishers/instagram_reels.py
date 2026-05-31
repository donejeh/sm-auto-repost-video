"""Instagram Reels publisher via Graph API."""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from backend.config import get_settings
from backend.publishers.base import PlatformCredentials, PublishOutcome

settings = get_settings()
API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


def publish_reel(
    video_path: Path,
    caption: str,
    creds: PlatformCredentials | None = None,
) -> PublishOutcome:
    token = creds.access_token if creds else settings.instagram_graph_access_token
    ig_id = creds.account_id if creds else settings.instagram_business_account_id
    if not token or not ig_id:
        return PublishOutcome(success=False, error="Missing Instagram credentials")

    try:
        with httpx.Client(timeout=300) as client:
            # Step 1: initialize upload session
            init_resp = client.post(
                f"{BASE}/{ig_id}/media",
                params={
                    "access_token": token,
                    "media_type": "REELS",
                    "upload_type": "resumable",
                    "caption": caption[:2200],
                },
            )
            if init_resp.status_code != 200:
                return PublishOutcome(success=False, error=init_resp.text)

            upload_uri = init_resp.json().get("uri")
            container_id = init_resp.json().get("id")
            if not upload_uri or not container_id:
                return PublishOutcome(success=False, error=f"Invalid init response: {init_resp.text}")

            # Step 2: upload binary
            video_bytes = video_path.read_bytes()
            up_resp = client.post(
                upload_uri,
                headers={
                    "Authorization": f"OAuth {token}",
                    "offset": "0",
                    "file_size": str(len(video_bytes)),
                    "Content-Type": "application/octet-stream",
                },
                content=video_bytes,
            )
            if up_resp.status_code not in (200, 201):
                return PublishOutcome(success=False, error=up_resp.text)

            # Step 3: poll status
            for _ in range(30):
                status_resp = client.get(
                    f"{BASE}/{container_id}",
                    params={"fields": "status_code", "access_token": token},
                )
                code = status_resp.json().get("status_code")
                if code == "FINISHED":
                    break
                if code == "ERROR":
                    return PublishOutcome(success=False, error=status_resp.text)
                time.sleep(5)
            else:
                return PublishOutcome(success=False, error="Instagram processing timeout")

            # Step 4: publish
            pub_resp = client.post(
                f"{BASE}/{ig_id}/media_publish",
                params={"creation_id": container_id, "access_token": token},
            )
            if pub_resp.status_code != 200:
                return PublishOutcome(success=False, error=pub_resp.text)

            post_id = pub_resp.json().get("id", container_id)
            return PublishOutcome(
                success=True,
                post_id=post_id,
                post_url=f"https://www.instagram.com/reel/{post_id}/",
            )
    except Exception as exc:
        return PublishOutcome(success=False, error=str(exc))

"""Facebook Reels / Page video publisher."""

from __future__ import annotations

import time
from pathlib import Path

import httpx

from backend.config import get_settings
from backend.publishers.base import PlatformCredentials, PublishOutcome

settings = get_settings()
API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


def _page_token(user_token: str, page_id: str) -> str:
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE}/{page_id}",
            params={"fields": "access_token", "access_token": user_token},
        )
        if resp.status_code == 200 and resp.json().get("access_token"):
            return resp.json()["access_token"]
    return user_token


def publish_facebook_reel(
    video_path: Path,
    caption: str,
    creds: PlatformCredentials | None = None,
) -> PublishOutcome:
    user_token = creds.access_token if creds else settings.instagram_graph_access_token
    page_id = creds.page_id if creds and creds.page_id else settings.facebook_page_id
    if not user_token or not page_id:
        return PublishOutcome(success=False, error="Missing Facebook Page credentials")

    token = _page_token(user_token, page_id)

    try:
        with httpx.Client(timeout=300) as client:
            init_resp = client.post(
                f"{BASE}/{page_id}/video_reels",
                params={
                    "access_token": token,
                    "upload_phase": "start",
                },
            )
            if init_resp.status_code != 200:
                # Fallback to standard video upload
                return _publish_page_video(client, page_id, token, video_path, caption)

            data = init_resp.json()
            upload_url = data.get("upload_url") or data.get("video_id")
            video_id = data.get("video_id")
            if not upload_url:
                return _publish_page_video(client, page_id, token, video_path, caption)

            video_bytes = video_path.read_bytes()
            up_resp = client.post(
                upload_url,
                headers={"Authorization": f"OAuth {token}"},
                files={"video_file": ("video.mp4", video_bytes, "video/mp4")},
            )
            if up_resp.status_code not in (200, 201):
                return PublishOutcome(success=False, error=up_resp.text)

            finish_resp = client.post(
                f"{BASE}/{page_id}/video_reels",
                params={
                    "access_token": token,
                    "upload_phase": "finish",
                    "video_id": video_id,
                    "description": caption[:63206],
                    "video_state": "PUBLISHED",
                },
            )
            if finish_resp.status_code != 200:
                return PublishOutcome(success=False, error=finish_resp.text)

            post_id = finish_resp.json().get("id") or video_id
            return PublishOutcome(
                success=True,
                post_id=str(post_id),
                post_url=f"https://www.facebook.com/{page_id}/posts/{post_id}",
            )
    except Exception as exc:
        return PublishOutcome(success=False, error=str(exc))


def _publish_page_video(client: httpx.Client, page_id: str, token: str, video_path: Path, caption: str) -> PublishOutcome:
    video_bytes = video_path.read_bytes()
    resp = client.post(
        f"{BASE}/{page_id}/videos",
        params={"access_token": token, "description": caption[:63206]},
        files={"source": ("video.mp4", video_bytes, "video/mp4")},
    )
    if resp.status_code != 200:
        return PublishOutcome(success=False, error=resp.text)
    post_id = resp.json().get("id")
    return PublishOutcome(
        success=True,
        post_id=str(post_id),
        post_url=f"https://www.facebook.com/{page_id}/videos/{post_id}",
    )

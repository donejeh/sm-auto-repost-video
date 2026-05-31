"""YouTube Shorts publisher."""

from __future__ import annotations

from pathlib import Path

from backend.publishers.base import PublishOutcome


def publish_youtube_short(
    video_path: Path,
    title: str,
    description: str,
    refresh_token: str | None = None,
) -> PublishOutcome:
    if not refresh_token:
        return PublishOutcome(success=False, error="YouTube not connected — connect via Settings")

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        from backend.config import get_settings

        s = get_settings()
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=s.google_client_id,
            client_secret=s.google_client_secret,
        )

        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title": title[:100],
                "description": (description + "\n\n#Shorts")[:5000],
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
        video_id = response.get("id")
        return PublishOutcome(
            success=True,
            post_id=video_id,
            post_url=f"https://www.youtube.com/shorts/{video_id}",
        )
    except Exception as exc:
        return PublishOutcome(success=False, error=str(exc))

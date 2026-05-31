"""Background worker tasks."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from backend.config import get_settings
from backend.db.models import Job, PublishResult
from backend.db.session import SessionLocal
from backend.publishers.base import PlatformCredentials
from backend.publishers.facebook_reels import publish_facebook_reel
from backend.publishers.instagram_reels import publish_reel
from backend.publishers.youtube_shorts import publish_youtube_short
from backend.services.crypto import decrypt_json
from backend.services.downloader import download_from_url
from backend.services.ffmpeg import export_final, generate_proxy, generate_thumbnail, probe_duration
from backend.services.job_events import log_event, update_job_status
from backend.services.slug import refresh_slug_from_title

settings = get_settings()


def job_dir(job_id: int) -> Path:
    return settings.storage_path / "jobs" / str(job_id)


def _get_meta_creds(db, user_id: int) -> PlatformCredentials | None:
    from backend.db.models import ConnectedAccount

    acct = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id, ConnectedAccount.provider == "meta")
        .first()
    )
    if acct:
        tokens = decrypt_json(acct.encrypted_tokens)
        return PlatformCredentials(
            access_token=tokens.get("access_token", ""),
            account_id=tokens.get("instagram_business_account_id", settings.instagram_business_account_id),
            page_id=tokens.get("facebook_page_id", settings.facebook_page_id),
        )
    if settings.instagram_graph_access_token:
        return PlatformCredentials(
            access_token=settings.instagram_graph_access_token,
            account_id=settings.instagram_business_account_id,
            page_id=settings.facebook_page_id,
        )
    return None


def _get_youtube_refresh(db, user_id: int) -> str | None:
    from backend.db.models import ConnectedAccount

    acct = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user_id, ConnectedAccount.provider == "google")
        .first()
    )
    if acct:
        return decrypt_json(acct.encrypted_tokens).get("refresh_token")
    return None


async def download_job(ctx, job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        update_job_status(db, job, "downloading", stage="import")
        log_event(db, job, "download_started", "Downloading source video")

        out = job_dir(job_id)
        last_logged_pct = [-1.0]

        def on_download_progress(message: str, percent: float | None) -> None:
            job.progress_message = message
            db.commit()
            if percent is None:
                return
            if percent - last_logged_pct[0] >= 4 or last_logged_pct[0] < 0:
                last_logged_pct[0] = percent
                log_event(db, job, "download_progress", message, {"percent": percent})

        if job.source_type == "url" and job.source_url:
            meta = download_from_url(job.source_url, out, on_progress=on_download_progress)
            job.source_path = meta["source_path"]
            job.source_platform = meta["platform"]
            job.title = meta["title"]
            if job.slug and meta["title"]:
                job.slug = refresh_slug_from_title(meta["title"], job.slug)
            job.duration_seconds = meta.get("duration")
        elif job.source_type == "upload" and job.source_path:
            log_event(db, job, "download_progress", "Saving upload…", {"percent": 30})
            source = Path(job.source_path)
            if source.parent != out:
                dest = out / "source.mp4"
                if source.resolve() != dest.resolve():
                    shutil.copy(source, dest)
                job.source_path = str(dest)
        elif job.source_path:
            shutil.copy(job.source_path, out / "source.mp4")
            job.source_path = str(out / "source.mp4")
        else:
            raise RuntimeError("No source URL or upload path")

        source = Path(job.source_path)
        if not job.duration_seconds:
            job.duration_seconds = probe_duration(source)

        log_event(db, job, "download_progress", "Creating preview…", {"percent": 94})
        update_job_status(db, job, "processing", stage="import")

        proxy = out / "proxy.mp4"
        generate_proxy(source, proxy)
        job.proxy_path = str(proxy)

        thumb = out / "thumb.jpg"
        generate_thumbnail(source, thumb)
        job.thumbnail_path = str(thumb)

        spec = job.edit_spec()
        if job.duration_seconds:
            spec["segments"] = [{"start": 0, "end": min(60, job.duration_seconds)}]
            job.set_edit_spec(spec)

        update_job_status(db, job, "ready", stage="edit")
        log_event(db, job, "download_complete", "Ready to edit", {"proxy": job.proxy_path})
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            update_job_status(db, job, "failed", error=str(exc))
            log_event(db, job, "error", str(exc), exc=exc)
    finally:
        db.close()


async def process_export_job(ctx, job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or not job.source_path:
            return
        update_job_status(db, job, "processing", stage="preview")
        log_event(db, job, "export_started", "Rendering final export")

        out = job_dir(job_id)
        export_path = out / "export.mp4"
        preview_path = out / "preview.mp4"
        spec = job.edit_spec()

        export_final(Path(job.source_path), export_path, spec, out)
        job.export_path = str(export_path)

        from backend.services.ffmpeg import export_preview

        export_preview(Path(job.source_path), preview_path, spec, out)

        update_job_status(db, job, "ready", stage="publish")
        log_event(db, job, "export_complete", "Export ready", {"export": str(export_path)})
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            update_job_status(db, job, "failed", error=str(exc))
            log_event(db, job, "error", str(exc), exc=exc)
    finally:
        db.close()


async def publish_job(ctx, job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job or not job.export_path:
            await process_export_job(ctx, job_id)
            job = db.get(Job, job_id)
            if not job or not job.export_path:
                return

        update_job_status(db, job, "publishing", stage="publish")
        log_event(db, job, "publish_started", "Publishing to platforms")

        video = Path(job.export_path)
        caption = job.caption or job.title or "AutoVideo"
        meta_creds = _get_meta_creds(db, job.user_id)
        yt_refresh = _get_youtube_refresh(db, job.user_id)

        for platform in job.publish_targets():
            log_event(db, job, "platform_started", f"Publishing to {platform}", {"platform": platform})
            if platform == "instagram":
                outcome = publish_reel(video, caption, meta_creds)
            elif platform == "facebook":
                outcome = publish_facebook_reel(video, caption, meta_creds)
            elif platform == "youtube":
                outcome = publish_youtube_short(
                    video, job.title or "Short", caption, refresh_token=yt_refresh
                )
            else:
                outcome = type("O", (), {"success": False, "error": "Unknown platform", "post_id": None, "post_url": None})()

            existing = (
                db.query(PublishResult)
                .filter(PublishResult.job_id == job.id, PublishResult.platform == platform)
                .first()
            )
            if existing:
                db.delete(existing)
            db.add(
                PublishResult(
                    job_id=job.id,
                    platform=platform,
                    success=outcome.success,
                    platform_post_id=outcome.post_id,
                    platform_post_url=outcome.post_url,
                    error_message=outcome.error,
                    posted_at=datetime.utcnow() if outcome.success else None,
                )
            )
            db.commit()
            log_event(
                db,
                job,
                "platform_complete" if outcome.success else "platform_failed",
                outcome.post_url or outcome.error or platform,
                {"platform": platform, "success": outcome.success},
            )

        update_job_status(db, job, "completed", stage="done")
        log_event(db, job, "publish_complete", "All platforms processed")
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            update_job_status(db, job, "failed", error=str(exc))
            log_event(db, job, "error", str(exc), exc=exc)
    finally:
        db.close()

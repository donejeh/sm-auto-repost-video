"""Job CRUD, upload, SSE."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import get_settings
from backend.db.models import Job, JobEvent, User
from backend.db.session import get_db
from backend.schemas import JobCreateUrl, JobOut, JobUpdate, PublishRequest
from backend.services.job_lookup import get_user_job
from backend.services.platform_detect import detect_platform
from backend.services.slug import make_initial_slug, refresh_slug_from_title
from backend.services.queue import enqueue_task
from backend.workers.tasks import job_dir

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
settings = get_settings()


def _job_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        slug=job.slug,
        status=job.status,
        stage=job.stage,
        source_type=job.source_type,
        source_url=job.source_url,
        source_platform=job.source_platform,
        title=job.title,
        duration_seconds=job.duration_seconds,
        thumbnail_path=job.thumbnail_path,
        proxy_path=job.proxy_path,
        export_path=job.export_path,
        edit_spec=job.edit_spec(),
        caption=job.caption,
        publish_targets=job.publish_targets(),
        progress_message=job.progress_message,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        publish_results=job.publish_results,
    )


@router.get("", response_model=list[JobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(100).all()
    return [_job_out(j) for j in jobs]


@router.post("", response_model=JobOut)
async def create_from_url(
    body: JobCreateUrl,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    platform = detect_platform(body.source_url)
    if platform == "unknown":
        raise HTTPException(status_code=400, detail="Unsupported video URL")

    job = Job(
        user_id=user.id,
        source_type="url",
        source_url=body.source_url,
        source_platform=platform,
        status="queued",
        stage="import",
        slug=make_initial_slug(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_dir(job.id).mkdir(parents=True, exist_ok=True)
    await enqueue_task("download_job", job.id)
    return _job_out(job)


@router.post("/upload", response_model=JobOut)
async def create_from_upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    ext = Path(file.filename).suffix.lower()
    if ext not in {".mp4", ".mov", ".webm", ".mkv"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    job = Job(
        user_id=user.id,
        source_type="upload",
        title=file.filename,
        source_platform="upload",
        status="queued",
        stage="import",
        slug=refresh_slug_from_title(file.filename, make_initial_slug()),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    out = job_dir(job.id)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"source{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    job.source_path = str(dest)
    db.commit()

    await enqueue_task("download_job", job.id)
    return _job_out(job)


@router.get("/{job_ref}", response_model=JobOut)
def get_job(job_ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_out(job)


@router.delete("/{job_ref}")
def delete_job(job_ref: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_id = job.id
    db.query(JobEvent).filter(JobEvent.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    shutil.rmtree(job_dir(job_id), ignore_errors=True)
    return {"ok": True}


@router.patch("/{job_ref}", response_model=JobOut)
def update_job(
    job_ref: str,
    body: JobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if body.edit_spec is not None:
        job.set_edit_spec(body.edit_spec)
    if body.caption is not None:
        job.caption = body.caption
    if body.publish_targets is not None:
        job.set_publish_targets(body.publish_targets)
    db.commit()
    db.refresh(job)
    return _job_out(job)


@router.post("/{job_ref}/export", response_model=JobOut)
async def trigger_export(
    job_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await enqueue_task("process_export_job", job.id)
    return _job_out(job)


@router.post("/{job_ref}/publish", response_model=JobOut)
async def trigger_publish(
    job_ref: str,
    body: PublishRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.set_publish_targets(body.platforms)
    if body.caption:
        job.caption = body.caption
    db.commit()
    await enqueue_task("publish_job", job.id)
    db.refresh(job)
    return _job_out(job)


@router.post("/{job_ref}/retry/{platform}", response_model=JobOut)
async def retry_platform(
    job_ref: str,
    platform: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.set_publish_targets([platform])
    db.commit()
    await enqueue_task("publish_job", job.id)
    db.refresh(job)
    return _job_out(job)


@router.get("/{job_ref}/validation")
def validate_job(
    job_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.publishers.validators import validate_export

    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    export = Path(job.export_path) if job.export_path else job_dir(job.id) / "export.mp4"
    warnings: dict[str, list[str]] = {}
    for platform in job.publish_targets() or ["instagram", "facebook", "youtube"]:
        platform_warnings = validate_export(platform, export)
        if platform_warnings:
            warnings[platform] = platform_warnings
    return {"warnings": warnings}


@router.get("/{job_ref}/media/{kind}")
def serve_media(
    job_ref: str,
    kind: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_id = job.id
    mapping = {
        "proxy": job.proxy_path,
        "export": job.export_path,
        "preview": str(job_dir(job_id) / "preview.mp4"),
        "thumb": job.thumbnail_path,
    }
    path = mapping.get(kind)
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Media not ready")
    return FileResponse(path)


@router.get("/{job_ref}/events")
async def job_events_sse(
    job_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_id = job.id

    async def stream():
        last_id = 0
        for _ in range(600):
            session = db.get_bind()
            from backend.db.session import SessionLocal

            s = SessionLocal()
            try:
                events = (
                    s.query(JobEvent)
                    .filter(JobEvent.job_id == job_id, JobEvent.id > last_id)
                    .order_by(JobEvent.id)
                    .all()
                )
                j = s.get(Job, job_id)
                for ev in events:
                    last_id = ev.id
                    payload = {
                        "id": ev.id,
                        "type": ev.event_type,
                        "message": ev.message,
                        "payload": json.loads(ev.payload_json) if ev.payload_json else None,
                        "status": j.status if j else None,
                        "stage": j.stage if j else None,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                if j and j.status in ("completed", "failed", "ready") and not events:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'status': j.status, 'stage': j.stage})}\n\n"
            finally:
                s.close()
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")

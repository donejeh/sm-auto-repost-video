"""Editor routes — audio overlay, captions upload."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.db.models import Job, User
from backend.db.session import get_db
from backend.schemas import JobOut
from backend.services.job_lookup import get_user_job
from backend.services.queue import enqueue_task
from backend.workers.tasks import job_dir

router = APIRouter(prefix="/api/jobs", tags=["editor"])


@router.post("/{job_ref}/audio-overlay")
async def upload_audio_overlay(
    job_ref: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out = job_dir(job.id)
    dest = out / f"overlay{Path(file.filename or 'audio.mp3').suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    spec = job.edit_spec()
    spec.setdefault("audio", {})["overlay_path"] = str(dest)
    job.set_edit_spec(spec)
    db.commit()
    return {"overlay_path": str(dest)}


@router.post("/{job_ref}/captions")
async def upload_captions(
    job_ref: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    out = job_dir(job.id)
    dest = out / "captions.srt"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    spec = job.edit_spec()
    spec["captions"] = {"mode": "burn_in", "srt_path": str(dest), "style": {"font_size": 24}}
    job.set_edit_spec(spec)
    db.commit()
    return {"srt_path": str(dest)}


@router.post("/{job_ref}/generate-captions")
async def generate_captions(
    job_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.source_path:
        raise HTTPException(status_code=400, detail="Source not ready")
    from backend.services.captions import extract_audio_from_video, audio_to_srt

    out = job_dir(job.id)
    wav = out / "audio.wav"
    srt = out / "captions.srt"
    extract_audio_from_video(Path(job.source_path), wav)
    audio_to_srt(wav, srt)
    spec = job.edit_spec()
    spec["captions"] = {"mode": "burn_in", "srt_path": str(srt), "style": {"font_size": 24}}
    job.set_edit_spec(spec)
    db.commit()
    return {"srt_path": str(srt)}


@router.post("/{job_ref}/preview", response_model=JobOut)
async def render_preview(
    job_ref: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.api.jobs import _job_out

    job = get_user_job(db, job_ref, user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await enqueue_task("process_export_job", job.id)
    db.refresh(job)
    return _job_out(job)

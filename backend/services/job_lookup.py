"""Resolve jobs by numeric id or slug."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.db.models import Job


def get_user_job(db: Session, ref: str, user_id: int) -> Job | None:
    if ref.isdigit():
        job = db.get(Job, int(ref))
        if job and job.user_id == user_id:
            return job
    job = db.query(Job).filter(Job.slug == ref, Job.user_id == user_id).first()
    return job

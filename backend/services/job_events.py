"""Job event helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.db.models import Job, JobEvent
from backend.logging_config import log_job_error

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    job: Job,
    event_type: str,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
    exc: BaseException | None = None,
) -> None:
    db.add(
        JobEvent(
            job_id=job.id,
            event_type=event_type,
            message=message,
            payload_json=json.dumps(payload) if payload else None,
        )
    )
    if message:
        job.progress_message = message
    db.commit()

    if event_type == "error" and message:
        log_job_error(job.id, job.stage or job.status, message, exc)
        logger.error("job=%s event=error %s", job.id, message, exc_info=exc)
    elif event_type == "platform_failed" and message:
        log_job_error(job.id, job.stage or job.status, message)
        logger.warning("job=%s platform_failed %s", job.id, message)


def update_job_status(
    db: Session,
    job: Job,
    status: str,
    stage: str | None = None,
    error: str | None = None,
) -> None:
    job.status = status
    if stage:
        job.stage = stage
    if error:
        job.last_error = error
    db.commit()

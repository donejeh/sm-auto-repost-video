"""Application logging — writes to logs/ for local investigation."""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.config import get_settings

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    log_dir = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "jobs").mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    root.addHandler(console)

    app_log = RotatingFileHandler(
        log_dir / "autovideo.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    app_log.setFormatter(fmt)
    root.addHandler(app_log)

    error_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s\n%(pathname)s:%(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    error_log = RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5_000_000,
        backupCount=10,
        encoding="utf-8",
    )
    error_log.setLevel(logging.ERROR)
    error_log.setFormatter(error_fmt)
    root.addHandler(error_log)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging initialized → %s", log_dir)


def log_job_error(
    job_id: int,
    stage: str,
    message: str,
    exc: BaseException | None = None,
) -> None:
    """Append a job-scoped error record for easier debugging."""
    settings = get_settings()
    job_log = settings.log_dir / "jobs" / f"job_{job_id}.log"
    job_log.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"[{stage}] {message}"]
    if exc is not None:
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    with open(job_log, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n\n")

    logger = logging.getLogger("autovideo.jobs")
    logger.error("job=%s stage=%s %s", job_id, stage, message, exc_info=exc)

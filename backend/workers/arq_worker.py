"""ARQ worker settings."""

from __future__ import annotations

from arq.connections import RedisSettings

from backend.config import get_settings
from backend.logging_config import setup_logging
from backend.workers import tasks

settings = get_settings()
setup_logging()


class WorkerSettings:
    functions = [tasks.download_job, tasks.process_export_job, tasks.publish_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url or "redis://localhost:6379")
    max_jobs = 2
    job_timeout = 600

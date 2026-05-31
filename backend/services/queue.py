"""Job queue — ARQ with Redis or SQLite polling fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def enqueue_task(task_name: str, job_id: int) -> None:
    if settings.use_redis:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis = RedisSettings.from_dsn(settings.redis_url)
        pool = await create_pool(redis)
        await pool.enqueue_job(task_name, job_id)
        await pool.close()
        logger.info("Enqueued %s for job %s via Redis", task_name, job_id)
    else:
        # Inline async execution for dev without Redis
        from backend.workers import tasks

        task_fn = getattr(tasks, task_name, None)
        if task_fn:
            asyncio.create_task(task_fn(None, job_id))
        logger.info("Running %s for job %s inline (no Redis)", task_name, job_id)

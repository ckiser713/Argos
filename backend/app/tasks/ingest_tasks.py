from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.domain.models import IngestStatus
from app.services.ingest_service import ingest_service
from app.worker import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=settings.task_max_retries,
)
def process_ingest_job_task(self, job_id: str) -> None:
    """
    Celery task entrypoint for ingest processing.
    Retries with exponential backoff and records status in the database.
    """
    try:
        asyncio.run(ingest_service.process_job(job_id, mark_failed=False))
    except Exception as exc:  # noqa: BLE001
        attempt = self.request.retries + 1
        max_attempts = settings.task_max_retries
        delay = min(
            settings.task_retry_backoff_seconds * (2 ** max(0, attempt - 1)),
            settings.task_retry_backoff_max_seconds,
        )
        if attempt >= max_attempts:
            asyncio.run(
                ingest_service.update_job(
                    job_id,
                    status=IngestStatus.FAILED,
                    message="Ingest failed after retries",
                    error_message=str(exc),
                    completed_at=datetime.now(timezone.utc),
                )
            )
            logger.exception("Ingest job %s failed after %s attempts", job_id, attempt)
            raise

        asyncio.run(
            ingest_service.update_job(
                job_id,
                status=IngestStatus.RUNNING,
                message=f"Retrying ingest in {delay}s (attempt {attempt}/{max_attempts})",
                error_message=str(exc),
            )
        )
        raise self.retry(exc=exc, countdown=delay)


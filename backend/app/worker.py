from __future__ import annotations

from celery import Celery

from app.config import get_settings


settings = get_settings()

celery_app = Celery(
    "argos",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.ingest_tasks"],
)

celery_app.conf.update(
    task_default_queue="ingest",
    task_always_eager=settings.tasks_eager,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"visibility_timeout": 60 * 60},
    task_default_retry_delay=settings.task_retry_backoff_seconds,
    task_time_limit=60 * 60,
)


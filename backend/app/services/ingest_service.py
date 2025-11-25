from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.domain.models import IngestJob, IngestStatus, IngestRequest


class IngestService:
    """
    In-memory ingest jobs.

    For now, jobs are created in QUEUED state; streaming endpoints advance them
    deterministically (QUEUED -> RUNNING -> COMPLETED/FAILED).
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, IngestJob] = {}

    def list_jobs(self) -> List[IngestJob]:
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[IngestJob]:
        return self._jobs.get(job_id)

    def create_job(self, request: IngestRequest) -> IngestJob:
        job_id = f"ingest_{len(self._jobs) + 1}"
        job = IngestJob(
            id=job_id,
            source_path=request.source_path,
            created_at=datetime.utcnow(),
            status=IngestStatus.QUEUED,
            progress=0.0,
            message="Job queued (stub).",
        )
        self._jobs[job_id] = job
        return job

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[IngestStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
    ) -> Optional[IngestJob]:
        job = self._jobs.get(job_id)
        if not job:
            return None

        data = job.model_dump()
        if status is not None:
            data["status"] = status
        if progress is not None:
            data["progress"] = progress
        if message is not None:
            data["message"] = message

        updated = IngestJob(**data)
        self._jobs[job_id] = updated
        return updated


ingest_service = IngestService()

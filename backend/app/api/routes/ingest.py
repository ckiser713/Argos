from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.domain.models import IngestJob, IngestRequest
from app.services.ingest_service import ingest_service

router = APIRouter()


@router.get("/jobs", response_model=List[IngestJob], summary="List ingest jobs")
def list_ingest_jobs() -> List[IngestJob]:
    return ingest_service.list_jobs()


@router.post(
    "/jobs",
    response_model=IngestJob,
    summary="Create a new ingest job",
)
def create_ingest_job(request: IngestRequest, background_tasks: BackgroundTasks) -> IngestJob:
    if not request.source_path:
        raise HTTPException(status_code=400, detail="source_path is required")
    job = ingest_service.create_job(request)
    background_tasks.add_task(ingest_service.process_job, job.id)
    return job

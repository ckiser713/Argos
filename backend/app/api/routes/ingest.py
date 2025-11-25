from typing import List

from fastapi import APIRouter, HTTPException

from app.domain.models import IngestJob, IngestRequest
from app.services.ingest_service import ingest_service

router = APIRouter()


@router.get("/jobs", response_model=List[IngestJob], summary="List ingest jobs")
def list_ingest_jobs() -> List[IngestJob]:
    return ingest_service.list_jobs()


@router.post(
    "/jobs",
    response_model=IngestJob,
    summary="Create a new ingest job (stubbed)",
)
def create_ingest_job(request: IngestRequest) -> IngestJob:
    if not request.source_path:
        raise HTTPException(status_code=400, detail="source_path is required")
    return ingest_service.create_job(request)

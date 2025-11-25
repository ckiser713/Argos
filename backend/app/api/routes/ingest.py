from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from app.domain.common import PaginatedResponse
from app.domain.models import IngestJob, IngestRequest, IngestStatus
from app.services.ingest_service import ingest_service
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Response, UploadFile

router = APIRouter()


@router.get(
    "/projects/{project_id}/ingest/jobs",
    response_model=PaginatedResponse,
    summary="List ingest jobs with filtering and pagination",
)
def list_ingest_jobs(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    stage: Optional[str] = Query(default=None),
    source_id: Optional[str] = Query(default=None),
) -> PaginatedResponse:
    jobs = ingest_service.list_jobs(
        project_id=project_id, cursor=cursor, limit=limit, status=status, stage=stage, source_id=source_id
    )
    return jobs


@router.get("/projects/{project_id}/ingest/jobs/{job_id}", response_model=IngestJob, summary="Get a single ingest job")
def get_ingest_job(project_id: str, job_id: str) -> IngestJob:
    job = ingest_service.get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return job


@router.post(
    "/projects/{project_id}/ingest/jobs", response_model=IngestJob, status_code=201, summary="Create a new ingest job"
)
def create_ingest_job(project_id: str, request: IngestRequest, background_tasks: BackgroundTasks) -> IngestJob:
    if not request.source_path:
        raise HTTPException(status_code=400, detail="source_path is required")
    job = ingest_service.create_job(project_id=project_id, request=request)
    background_tasks.add_task(ingest_service.process_job, job.id)
    return job


@router.post(
    "/projects/{project_id}/ingest/jobs/{job_id}/cancel",
    response_model=IngestJob,
    summary="Cancel a running ingest job",
)
def cancel_ingest_job(project_id: str, job_id: str) -> IngestJob:
    job = ingest_service.get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest job not found")

    if job.status not in [IngestStatus.QUEUED, IngestStatus.RUNNING]:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled. Current status: {job.status.value}")

    return ingest_service.cancel_job(job_id)


@router.delete("/projects/{project_id}/ingest/jobs/{job_id}", status_code=204, summary="Delete an ingest job")
def delete_ingest_job(project_id: str, job_id: str):
    job = ingest_service.get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest job not found")

    if job.status == IngestStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Cannot delete job with status RUNNING. Cancel the job first.")

    ingest_service.delete_job(job_id)
    return Response(status_code=204)


@router.post("/projects/{project_id}/ingest/upload")
async def upload_file(project_id: str, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    file_path = temp_dir / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    job = ingest_service.create_job(project_id=project_id, request=IngestRequest(source_path=str(file_path)))
    background_tasks.add_task(ingest_service.process_job, job.id)

    return {"filename": file.filename, "job_id": job.id}

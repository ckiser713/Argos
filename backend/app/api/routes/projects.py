from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.domain.common import PaginatedResponse
from app.domain.project import (
    CortexProject,
    CreateProjectRequest,
    DeleteProjectResponse,
    UpdateProjectRequest,
)
from app.services.project_service import ProjectService, get_project_service

router = APIRouter(prefix="/projects")


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    service: ProjectService = Depends(get_project_service),
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    return service.list_projects(cursor=cursor, limit=limit)


@router.post("", response_model=CortexProject, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> CortexProject:
    return service.create_project(body)


@router.get("/{project_id}", response_model=CortexProject)
async def get_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> CortexProject:
    return service.get_project(project_id)


@router.patch("/{project_id}", response_model=CortexProject)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    service: ProjectService = Depends(get_project_service),
) -> CortexProject:
    return service.update_project(project_id, body)


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> DeleteProjectResponse:
    return service.delete_project(project_id)

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

from app.domain.common import PaginatedResponse
from app.domain.project import (
    CortexProject,
    CreateProjectRequest,
    DeleteProjectResponse,
    ProjectFactory,
    UpdateProjectRequest,
)
from app.repos.project_repo import ProjectRepository, get_project_repo


class ProjectService:
    def __init__(self, repo: ProjectRepository) -> None:
        self.repo = repo

    def list_projects(self, *, cursor: Optional[str], limit: int) -> PaginatedResponse:
        return self.repo.list_projects(cursor=cursor, limit=limit)

    def get_project(self, project_id: str) -> CortexProject:
        project = self.repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    def create_project(self, request: CreateProjectRequest) -> CortexProject:
        if request.slug:
            normalized_slug = request.slug
            if self.repo.get_by_slug(normalized_slug):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
        else:
            base_slug = ProjectFactory._slugify(request.name)
            normalized_slug = self._ensure_unique_slug(base_slug)

        project = ProjectFactory.new(request.name, normalized_slug, request.description)
        return self.repo.save(project)

    def _ensure_unique_slug(self, base_slug: str) -> str:
        slug = base_slug
        counter = 1
        while self.repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def update_project(self, project_id: str, request: UpdateProjectRequest) -> CortexProject:
        current = self.repo.get_project(project_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        fields = request.model_dump(exclude_none=True)
        updated = self.repo.update(project_id, fields=fields)
        if not updated:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update project")
        return updated

    def delete_project(self, project_id: str) -> DeleteProjectResponse:
        deleted = self.repo.delete(project_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return DeleteProjectResponse(success=True)


def get_project_service() -> ProjectService:
    return ProjectService(get_project_repo())

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.common import to_camel


class CortexProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DRAFT = "draft"


class CortexProject(BaseModel):
    id: str
    slug: str
    name: str
    description: Optional[str] = None
    status: CortexProjectStatus = Field(default=CortexProjectStatus.ACTIVE)
    created_at: datetime
    updated_at: datetime
    default_model_role_id: Optional[str] = None
    root_idea_cluster_id: Optional[str] = None
    roadmap_id: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CreateProjectRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CortexProjectStatus] = Field(default=None)
    default_model_role_id: Optional[str] = None
    root_idea_cluster_id: Optional[str] = None
    roadmap_id: Optional[str] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DeleteProjectResponse(BaseModel):
    success: bool = True

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectFactory:
    @staticmethod
    def new(name: str, slug: Optional[str], description: Optional[str]) -> CortexProject:
        project_id = uuid4().hex
        normalized_slug = slug or ProjectFactory._slugify(name)
        now = datetime.now(timezone.utc)
        return CortexProject(
            id=project_id,
            slug=normalized_slug,
            name=name,
            description=description,
            status=CortexProjectStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _slugify(value: str) -> str:
        return "-".join(value.lower().split())

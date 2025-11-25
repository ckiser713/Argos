from __future__ import annotations

import logging
from typing import Optional

from app.domain.mode import ExecutionMode, ProjectExecutionSettings
from app.repos import mode_repo
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["mode"])


class ProjectExecutionSettingsUpdateRequest(BaseModel):
    mode: Optional[ExecutionMode] = Field(None, description="Execution mode: 'normal' or 'paranoid'")
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Base temperature for LLM calls")
    validation_passes: Optional[int] = Field(None, ge=1, le=10, description="Number of validation passes")
    max_parallel_tools: Optional[int] = Field(None, ge=1, le=64, description="Maximum parallel tools/subtasks")


@router.get(
    "/{project_id}/mode",
    response_model=ProjectExecutionSettings,
    summary="Get project execution settings",
)
def get_project_mode(project_id: str) -> ProjectExecutionSettings:
    """
    Get the current execution mode and related settings for a project.
    """
    return mode_repo.get_project_settings(project_id)


@router.patch(
    "/{project_id}/mode",
    response_model=ProjectExecutionSettings,
    summary="Update project execution settings",
)
def update_project_mode(
    project_id: str,
    body: ProjectExecutionSettingsUpdateRequest,
) -> ProjectExecutionSettings:
    """Update execution mode and/or overrides for a project.

    Frontend can drive this via a simple Normal/Paranoid toggle; advanced users
    can also tune temperature, validation passes, and max parallel tools.
    """
    current = mode_repo.get_project_settings(project_id=project_id)

    # Reject no-op payloads for clarity.
    if (
        body.mode is None
        and body.llm_temperature is None
        and body.validation_passes is None
        and body.max_parallel_tools is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "At least one field (mode, llm_temperature, validation_passes, max_parallel_tools) must be provided."
            ),
        )

    updated = current.copy(
        update={
            "mode": body.mode if body.mode is not None else current.mode,
            "llm_temperature": (body.llm_temperature if body.llm_temperature is not None else current.llm_temperature),
            "validation_passes": (
                body.validation_passes if body.validation_passes is not None else current.validation_passes
            ),
            "max_parallel_tools": (
                body.max_parallel_tools if body.max_parallel_tools is not None else current.max_parallel_tools
            ),
        }
    )

    saved = mode_repo.set_project_settings(updated)

    logger.info(
        "mode_api.project_mode_updated",
        extra={
            "project_id": project_id,
            "mode": saved.mode,
            "temperature": saved.llm_temperature,
            "validation_passes": saved.validation_passes,
            "max_parallel_tools": saved.max_parallel_tools,
        },
    )

    return saved

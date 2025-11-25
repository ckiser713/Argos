from __future__ import annotations

import logging
from typing import Dict

from app.config import get_settings
from app.domain.mode import ExecutionMode, ProjectExecutionSettings

logger = logging.getLogger(__name__)

# In-memory store for project settings.
# In a real application, this would be backed by a database.
_PROJECT_SETTINGS_STORE: Dict[str, ProjectExecutionSettings] = {}


def _build_default_settings(project_id: str, mode: ExecutionMode) -> ProjectExecutionSettings:
    """Builds default settings for a project based on the configured mode."""
    settings = get_settings()

    if mode == "paranoid":
        return ProjectExecutionSettings(
            project_id=project_id,
            mode="paranoid",
            llm_temperature=settings.paranoid_mode_llm_temperature,
            validation_passes=settings.paranoid_mode_validation_passes,
            max_parallel_tools=settings.paranoid_mode_max_parallel_tools,
        )

    # Default: normal mode
    return ProjectExecutionSettings(
        project_id=project_id,
        mode="normal",
        llm_temperature=settings.normal_mode_llm_temperature,
        validation_passes=settings.normal_mode_validation_passes,
        max_parallel_tools=settings.normal_mode_max_parallel_tools,
    )


def get_project_settings(project_id: str) -> ProjectExecutionSettings:
    """Fetch per-project execution settings, falling back to global defaults.

    This is safe to call from hot paths (LLM + LangGraph) because it is O(1) and
    keeps a small in-memory cache. When backed by a DB later, this function
    should be wrapped with appropriate caching.
    """
    if project_id in _PROJECT_SETTINGS_STORE:
        return _PROJECT_SETTINGS_STORE[project_id]

    default_settings = _build_default_settings(project_id=project_id, mode="normal")
    _PROJECT_SETTINGS_STORE[project_id] = default_settings

    logger.info(
        "mode_repo.default_settings_created",
        extra={
            "project_id": project_id,
            "mode": default_settings.mode,
            "temperature": default_settings.llm_temperature,
            "validation_passes": default_settings.validation_passes,
            "max_parallel_tools": default_settings.max_parallel_tools,
        },
    )
    return default_settings


def set_project_settings(
    new_settings: ProjectExecutionSettings,
) -> ProjectExecutionSettings:
    """Upsert project execution settings.

    The caller should supply a fully-validated `ProjectExecutionSettings` object.
    """
    _PROJECT_SETTINGS_STORE[new_settings.project_id] = new_settings

    logger.info(
        "mode_repo.settings_updated",
        extra={
            "project_id": new_settings.project_id,
            "mode": new_settings.mode,
            "temperature": new_settings.llm_temperature,
            "validation_passes": new_settings.validation_passes,
            "max_parallel_tools": new_settings.max_parallel_tools,
        },
    )
    return new_settings

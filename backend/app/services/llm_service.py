from __future__ import annotations

import logging
from typing import Any, Dict

from app.repos.mode_repo import get_project_settings
from app.domain.mode import ProjectExecutionSettings

logger = logging.getLogger(__name__)


def _call_underlying_llm(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    model: str,
    **extra_kwargs: Any,
) -> str:
    """Thin wrapper around your actual inference stack (vLLM, llama.cpp, etc.).

    This function is intentionally kept small and mode-agnostic; callers should
    perform mode lookups before invoking it.
    """
    # TODO: replace with the actual integration to your model runtime.
    logger.warning("Using dummy LLM client for: %s", prompt[:50])
    return f"dummy-response for: {prompt[:50]}..."


def generate_text(
    prompt: str,
    project_id: str,
    *,
    base_temperature: float,
    max_tokens: int = 500,
    model: str = "default_llm",
    **extra_kwargs: Any,
) -> str:
    """
    Generates text using the underlying LLM, with mode-aware adjustments.
    """
    settings: ProjectExecutionSettings = get_project_settings(project_id)

    # Use project-specific temperature, overriding the base.
    temperature = settings.llm_temperature

    logger.info(
        "llm_service.generate_text.start",
        extra={
            "project_id": project_id,
            "mode": settings.mode,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": model,
        },
    )

    # --- primary generation pass ---
    raw_response = _call_underlying_llm(
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        **extra_kwargs,
    )

    if settings.mode == "normal":
        return raw_response

    # --- paranoid mode: checker / validation passes ---
    validated = raw_response

    for i in range(settings.validation_passes):
        checker_prompt = (
            "You are a careful reviewer. Given the user prompt and the draft answer,"
            " identify any factual inconsistencies, unsafe suggestions, or missing steps,"
            " then provide a corrected / improved final answer.\n\n"
            f"USER PROMPT:\n{prompt}\n\nDRAFT ANSWER:\n{validated}"
        )

        logger.info(
            "llm_service.generate_text.paranoid_checker_pass",
            extra={
                "project_id": project_id,
                "pass_index": i,
                "mode": settings.mode,
            },
        )

        validated = _call_underlying_llm(
            checker_prompt,
            temperature=min(temperature, 0.2), # Checker LLM usually benefits from lower temp
            max_tokens=max_tokens,
            model=model,
            **extra_kwargs,
        )

    return validated

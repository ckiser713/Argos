from __future__ import annotations

import logging
from typing import Any

import openai

from app.config import get_settings
from app.domain.mode import ProjectExecutionSettings
from app.repos.mode_repo import get_project_settings

logger = logging.getLogger(__name__)

settings = get_settings()

client = openai.OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def get_llm_client() -> openai.OpenAI:
    return client


def _call_underlying_llm(
    prompt: str, *, temperature: float, max_tokens: int, model: str = None, json_mode: bool = False, **kwargs
) -> str:
    target_model = model or settings.llm_model_name

    try:
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM Error: {str(e)}"


def generate_text(
    prompt: str,
    project_id: str,
    *,
    base_temperature: float,
    max_tokens: int = 500,
    model: str = "default_llm",
    json_mode: bool = False,
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
            "json_mode": json_mode,
        },
    )

    # --- primary generation pass ---
    raw_response = _call_underlying_llm(
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        json_mode=json_mode,
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
            temperature=min(temperature, 0.2),  # Checker LLM usually benefits from lower temp
            max_tokens=max_tokens,
            model=model,
            **extra_kwargs,
        )

    return validated

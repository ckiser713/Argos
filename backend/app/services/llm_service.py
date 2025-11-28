from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import Any

import openai

from app.config import get_settings
from app.domain.mode import ProjectExecutionSettings
from app.repos.mode_repo import get_project_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize OpenAI client (for vLLM/Ollama API backend)
client = openai.OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


class ModelLane(StrEnum):
    ORCHESTRATOR = "orchestrator"
    CODER = "coder"
    SUPER_READER = "super_reader"
    FAST_RAG = "fast_rag"
    GOVERNANCE = "governance"


def get_llm_client(base_url: str = None) -> openai.OpenAI:
    if base_url and base_url != settings.llm_base_url:
        return openai.OpenAI(base_url=base_url, api_key=settings.llm_api_key)
    return client


def resolve_lane_config(lane: ModelLane) -> tuple[str, str, str]:
    """
    Resolve base_url, model_name, and backend for the given lane.
    
    Returns (base_url, model_name, backend)
    """
    lane_name = lane.value.upper()
    
    # Check for lane-specific config
    base_url_attr = f"lane_{lane.value}_url"
    model_attr = f"lane_{lane.value}_model"
    
    base_url = getattr(settings, base_url_attr, "")
    model_name = getattr(settings, model_attr, "")
    
    if base_url and model_name:
        # Determine backend based on URL or default
        if "8080" in base_url or lane == ModelLane.SUPER_READER:
            backend = "llama_cpp"
        else:
            backend = "openai"
        return base_url, model_name, backend
    
    # Fallback to default
    fallback_lane = ModelLane(settings.llm_default_lane)
    if fallback_lane == lane:
        return settings.llm_base_url, settings.llm_model_name, settings.llm_backend
    
    # Recursive fallback
    return resolve_lane_config(fallback_lane)


def _call_underlying_llm(
    prompt: str, *, temperature: float, max_tokens: int, base_url: str = None, model: str = None, backend: str = None, json_mode: bool = False, **kwargs
) -> str:
    """
    Call the underlying LLM backend (OpenAI API or llama.cpp).
    
    Backend selection is controlled by CORTEX_LLM_BACKEND or per-lane.
    """
    effective_backend = backend or settings.llm_backend.lower()
    
    if effective_backend == "llama_cpp":
        # Use llama.cpp service
        try:
            from app.services.llama_cpp_service import get_llama_cpp_service
            
            llama_service = get_llama_cpp_service()
            
            # llama.cpp doesn't support json_mode directly, but we can try to parse JSON
            response = llama_service.generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            
            # If json_mode requested, try to extract JSON from response
            if json_mode:
                # Simple heuristic: look for JSON object in response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json_match.group(0)
                # If no JSON found, wrap response in JSON object
                return f'{{"response": {json.dumps(response)}}}'
            
            return response
            
        except ImportError:
            logger.warning(
                "llama_cpp_service not available, falling back to OpenAI API",
                extra={"backend": effective_backend}
            )
            # Fall through to OpenAI API
        except Exception as e:
            logger.error(
                "llama_cpp_service error, falling back to OpenAI API",
                extra={"error": str(e), "backend": effective_backend}
            )
            # Fall through to OpenAI API
    
    # Default: Use OpenAI-compatible API (vLLM/Ollama)
    target_model = model or settings.llm_model_name
    target_client = get_llm_client(base_url)

    try:
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        response = target_client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("OpenAI API error", extra={"error": str(e)})
        return f"LLM Error: {str(e)}"


def generate_text(
    prompt: str,
    project_id: str,
    lane: ModelLane = ModelLane.ORCHESTRATOR,
    *,
    temperature: float | None = None,
    max_tokens: int = 1000,
    json_mode: bool = False
) -> str:
    """
    Generates text using the underlying LLM, with mode-aware adjustments and lane routing.
    """
    settings_obj: ProjectExecutionSettings = get_project_settings(project_id)

    # Resolve lane configuration
    base_url, model_name, backend = resolve_lane_config(lane)

    # Use project-specific temperature, or provided, or default
    effective_temperature = temperature if temperature is not None else settings_obj.llm_temperature

    logger.info(
        "llm_service.generate_text.start",
        extra={
            "project_id": project_id,
            "mode": settings_obj.mode,
            "lane": lane.value,
            "base_url": base_url,
            "model": model_name,
            "backend": backend,
            "temperature": effective_temperature,
            "max_tokens": max_tokens,
            "json_mode": json_mode,
        },
    )

    # --- primary generation pass ---
    raw_response = _call_underlying_llm(
        prompt,
        temperature=effective_temperature,
        max_tokens=max_tokens,
        base_url=base_url,
        model=model_name,
        backend=backend,
        json_mode=json_mode,
    )

    if settings_obj.mode == "normal":
        return raw_response

    # --- paranoid mode: checker / validation passes ---
    validated = raw_response

    for i in range(settings_obj.validation_passes):
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
                "mode": settings_obj.mode,
                "lane": lane.value,
            },
        )

        validated = _call_underlying_llm(
            checker_prompt,
            temperature=min(effective_temperature, 0.2),  # Checker LLM usually benefits from lower temp
            max_tokens=max_tokens,
            base_url=base_url,
            model=model_name,
            backend=backend,
        )

    return validated

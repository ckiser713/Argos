from __future__ import annotations

import json
import logging
import re
from enum import StrEnum
from typing import Any, List, Optional

import openai
from pydantic import BaseModel

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


class LLMResponse(BaseModel):
    response: str
    reasoning_trace: Optional[List[str]] = None
    status: str = "ok"


def get_llm_client(base_url: str = None) -> openai.OpenAI:
    if base_url and base_url != settings.llm_base_url:
        return openai.OpenAI(base_url=base_url, api_key=settings.llm_api_key)
    return client


def resolve_lane_config(lane: ModelLane) -> tuple[str, str, str]:
    """
    Resolve base_url, model_name, and backend for the given lane.
    
    Returns (base_url, model_name, backend)
    Raises ValueError if no configuration found and fallback fails
    """
    lane_name = lane.value.upper()
    
    base_url = getattr(settings, f"lane_{lane.value}_url", "")
    model_name = getattr(settings, f"lane_{lane.value}_model", "")
    backend = getattr(settings, f"lane_{lane.value}_backend", "")
    
    if base_url and model_name:
        if not backend:
            backend = "openai" if "8080" not in base_url else "llama_cpp"
        return base_url, model_name, backend
    
    fallback_lane = ModelLane(settings.llm_default_lane)
    if fallback_lane == lane:
        return settings.llm_base_url, settings.llm_model_name, settings.llm_backend
    
    logger.warning(
        f"Lane {lane.value} not configured, falling back to {fallback_lane.value}",
        extra={"lane": lane.value, "fallback": fallback_lane.value}
    )
    return resolve_lane_config(fallback_lane)


def _call_underlying_llm(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    base_url: str = None,
    model: str = None,
    backend: str = None,
    lane: ModelLane = None,
    json_mode: bool = False,
    image_data: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Call the underlying LLM backend (OpenAI API or llama.cpp).
    """
    effective_backend = backend or settings.llm_backend.lower()
    
    if effective_backend == "llama_cpp":
        try:
            from app.services.llama_cpp_service import get_llama_cpp_service
            
            model_path_attr = f"lane_{lane.value}_model_path" if lane else ""
            model_path = getattr(settings, model_path_attr, "") or None
            
            llama_service = get_llama_cpp_service(model_path=model_path)
            response = llama_service.generate(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
            
            if json_mode:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                return json_match.group(0) if json_match else f'{{"response": {json.dumps(response)}}}'
            return response
            
        except ImportError:
            logger.warning("llama_cpp_service not available, falling back to OpenAI API")
        except Exception as e:
            logger.error(f"llama_cpp_service error, falling back to OpenAI API: {e}")

    # Default: Use OpenAI-compatible API (vLLM/Ollama)
    target_model = model or settings.llm_model_name
    target_client = get_llm_client(base_url)

    messages = []
    if image_data and lane == ModelLane.FAST_RAG:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            ],
        })
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        response_format = {"type": "json_object"} if json_mode else {"type": "text"}
        response = target_client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return f"LLM Error: {str(e)}"


def generate_text(
    prompt: str,
    project_id: str,
    lane: ModelLane = ModelLane.ORCHESTRATOR,
    *,
    temperature: float | None = None,
    max_tokens: int = 4096,
    json_mode: bool = False,
    image_data: Optional[str] = None,
) -> LLMResponse:
    """
    Generates text using the underlying LLM, with mode-aware adjustments and lane routing.
    """
    if settings.cortex_mode == "INGEST":
        logger.info("Request received in INGEST mode, queuing for later processing.")
        return LLMResponse(response="Request has been queued and will be processed when ingest is complete.", status="queued")

    settings_obj: ProjectExecutionSettings = get_project_settings(project_id)
    base_url, model_name, backend = resolve_lane_config(lane)
    effective_temperature = settings_obj.llm_temperature if temperature is None else temperature

    logger.info(
        "llm_service.generate_text.start",
        extra={"project_id": project_id, "lane": lane.value, "model": model_name, "backend": backend},
    )

    final_response = _call_underlying_llm(
        prompt,
        temperature=effective_temperature,
        max_tokens=max_tokens,
        base_url=base_url,
        model=model_name,
        backend=backend,
        lane=lane,
        json_mode=json_mode,
        image_data=image_data,
    )

    if settings_obj.mode == "paranoid":
        for i in range(settings_obj.validation_passes):
            checker_prompt = f"Review the following prompt and draft answer. Identify inconsistencies or missing steps and provide a corrected final answer.\n\nPROMPT:\n{prompt}\n\nDRAFT:\n{final_response}"
            final_response = _call_underlying_llm(
                checker_prompt,
                temperature=min(effective_temperature, 0.2),
                max_tokens=max_tokens,
                base_url=base_url,
                model=model_name,
                backend=backend,
                lane=lane,
            )

    # Handle Chain of Thought for ORCHESTRATOR lane
    if lane == ModelLane.ORCHESTRATOR:
        reasoning_trace = re.findall(r"<think>(.*?)</think>", final_response, re.DOTALL)
        clean_response = re.sub(r"<think>.*?</think>", "", final_response, flags=re.DOTALL).strip()
        return LLMResponse(response=clean_response, reasoning_trace=reasoning_trace or None)

    return LLMResponse(response=final_response)

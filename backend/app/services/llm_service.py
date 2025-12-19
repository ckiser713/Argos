import asyncio
import concurrent.futures
import json
import logging
import re
from typing import Any, List, Optional

from pydantic import BaseModel

from app.config import get_settings
from app.domain.mode import ProjectExecutionSettings
from app.domain.model_lanes import ModelLane, is_vllm_lane
from app.observability import record_model_call
from app.repos.mode_repo import get_project_settings
from app.services.local_llm_client import get_local_llm_client
from app.services.model_registry import (
    get_lane_backend,
    get_lane_default_path,
    get_lane_model_name,
)
from app.services.vllm_lane_manager import get_lane_manager

logger = logging.getLogger(__name__)


def get_llm_client(base_url: Optional[str] = None):
    """Return a local LLM client for the given base_url."""
    return get_local_llm_client(base_url=base_url)


class LLMResponse(BaseModel):
    response: str
    reasoning_trace: Optional[List[str]] = None
    status: str = "ok"

    def __getattr__(self, item: str):
        if hasattr(self.response, item):
            return getattr(self.response, item)
        raise AttributeError(f"LLMResponse has no attribute {item}")

def resolve_lane_config(lane: ModelLane) -> tuple[str, str, str, str]:
    """
    Resolve base_url, model_name, backend, and model_path for the given lane.
    """
    runtime_settings = get_settings()
    lane_value = lane.value
    base_url = getattr(runtime_settings, f"lane_{lane_value}_url", "")
    model_name = getattr(runtime_settings, f"lane_{lane_value}_model", "") or get_lane_model_name(lane)
    model_path = getattr(runtime_settings, f"lane_{lane_value}_model_path", "") or get_lane_default_path(lane)
    backend = getattr(runtime_settings, f"lane_{lane_value}_backend", "") or get_lane_backend(lane)

    if not base_url:
        base_url = (
            runtime_settings.lane_orchestrator_url
            if is_vllm_lane(lane)
            else runtime_settings.lane_super_reader_url
        )

    return base_url, model_name, backend, model_path


def get_routed_llm_config(prompt: str) -> tuple[str, str, str, str]:
    """
    Legacy routing hook retained for compatibility.

    Returns (base_url, model_name, backend, model_path).
    """
    return resolve_lane_config(ModelLane.ORCHESTRATOR)


def _call_underlying_llm(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    base_url: str = None,
    model: str = None,
    backend: str = None,
    model_path: str = None,
    json_mode: bool = False,
    image_data: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Call the underlying LLM backend (OpenAI API or llama.cpp).
    """
    runtime_settings = get_settings()
    effective_backend = (backend or runtime_settings.llm_backend).lower()
    backend_label = effective_backend

    if effective_backend == "llama_cpp" and not base_url:
        try:
            from app.services.llama_cpp_service import get_llama_cpp_service
            
            llama_service = get_llama_cpp_service(model_path=model_path)
            response = llama_service.generate(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
            
            if json_mode:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                result = json_match.group(0) if json_match else f'{{"response": {json.dumps(response)}}}'
            else:
                result = response
            record_model_call("llama_cpp", model or runtime_settings.llm_model_name, True)
            return result
            
        except ImportError:
            logger.warning("llama_cpp_service not available, falling back to OpenAI API")
            record_model_call("llama_cpp", model or runtime_settings.llm_model_name, False)
        except Exception as e:
            logger.error(f"llama_cpp_service error, falling back to OpenAI API: {e}")
            record_model_call("llama_cpp", model or runtime_settings.llm_model_name, False)

    # Default: Use OpenAI-compatible API (vLLM/Ollama)
    target_model = model or runtime_settings.llm_model_name
    target_client = get_llm_client(base_url)

    messages = []
    # Vision capabilities are typically with more advanced models, so keeping this part simple
    if image_data:
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
        response_format = {"type": "json_object"} if json_mode else None
        response = target_client.chat_completions_create(
            model=target_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        record_model_call(backend_label, target_model, True)
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Local LLM API error: {e}")
        record_model_call(backend_label, target_model, False)
        return f"LLM Error: {str(e)}"


async def generate_text_async(
    prompt: str,
    project_id: str,
    *,
    lane: ModelLane = ModelLane.ORCHESTRATOR,
    temperature: float | None = None,
    max_tokens: int = 4096,
    json_mode: bool = False,
    image_data: Optional[str] = None,
) -> LLMResponse:
    """
    Generates text using the underlying LLM, with mode-aware adjustments and lane routing.
    """
    runtime_settings = get_settings()

    if runtime_settings.argos_mode == "INGEST":
        logger.info("Request received in INGEST mode, queuing for later processing.")
        return LLMResponse(
            response="Request has been queued and will be processed when ingest is complete.",
            status="queued",
        )

    settings_obj: ProjectExecutionSettings = get_project_settings(project_id)

    base_url, model_name, backend, model_path = resolve_lane_config(lane)
    target_lane = lane

    if is_vllm_lane(lane):
        lane_manager = get_lane_manager()
        if not await lane_manager.ensure_lane(lane):
            vllm_healthy = await lane_manager.is_vllm_healthy()
            record_model_call(backend, model_name, False)
            if vllm_healthy and lane != ModelLane.ORCHESTRATOR:
                target_lane = ModelLane.ORCHESTRATOR
            else:
                target_lane = ModelLane.SUPER_READER
            logger.warning(
                "Lane switch failed; falling back to %s",
                target_lane.value,
                extra={"lane": lane.value, "fallback": target_lane.value},
            )
            base_url, model_name, backend, model_path = resolve_lane_config(target_lane)
            if is_vllm_lane(target_lane) and not await lane_manager.ensure_lane(target_lane):
                record_model_call(backend, model_name, False)
                target_lane = ModelLane.SUPER_READER
                base_url, model_name, backend, model_path = resolve_lane_config(target_lane)

    effective_temperature = settings_obj.llm_temperature if temperature is None else temperature

    logger.info(
        "llm_service.generate_text.start",
        extra={
            "project_id": project_id,
            "model": model_name,
            "backend": backend,
            "lane": target_lane.value,
        },
    )

    final_response = await asyncio.to_thread(
        _call_underlying_llm,
        prompt,
        temperature=effective_temperature,
        max_tokens=max_tokens,
        base_url=base_url,
        model=model_name,
        backend=backend,
        model_path=model_path,
        json_mode=json_mode,
        image_data=image_data,
    )

    if settings_obj.mode == "paranoid":
        for _ in range(settings_obj.validation_passes):
            checker_prompt = (
                "Review the following prompt and draft answer. Identify inconsistencies or missing steps "
                "and provide a corrected final answer.\n\nPROMPT:\n"
                f"{prompt}\n\nDRAFT ANSWER:\n{final_response}"
            )
            final_response = await asyncio.to_thread(
                _call_underlying_llm,
                checker_prompt,
                temperature=min(effective_temperature, 0.2),
                max_tokens=max_tokens,
                base_url=base_url,
                model=model_name,
                backend=backend,
                model_path=model_path,
            )

    # Chain of Thought might not be standard across all models.
    # Consider making this conditional on the route if needed.
    reasoning_trace = re.findall(r"<think>(.*?)</think>", final_response, re.DOTALL)
    clean_response = re.sub(r"<think>.*?</think>", "", final_response, flags=re.DOTALL).strip()
    return LLMResponse(response=clean_response, reasoning_trace=reasoning_trace or None)


def generate_text(
    prompt: str,
    project_id: str,
    *,
    lane: ModelLane = ModelLane.ORCHESTRATOR,
    temperature: float | None = None,
    max_tokens: int = 4096,
    json_mode: bool = False,
    image_data: Optional[str] = None,
) -> LLMResponse:
    """
    Synchronous wrapper for generate_text_async.
    """
    coro = generate_text_async(
        prompt=prompt,
        project_id=project_id,
        lane=lane,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
        image_data=image_data,
    )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

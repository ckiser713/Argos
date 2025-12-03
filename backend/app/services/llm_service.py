import json
import logging
import re
from typing import Any, List, Optional

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate # Combined
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel

from app.config import get_settings
from app.domain.mode import ProjectExecutionSettings
from app.repos.mode_repo import get_project_settings
from app.services.local_llm_client import get_local_llm_client, LocalChatLLM

logger = logging.getLogger(__name__)

settings = get_settings()


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

# --- LangChain Semantic Routing Setup ---

SIMPLE_ROUTE_NAME = "simple"
COMPLEX_ROUTE_NAME = "complex"

ROUTE_DESCRIPTIONS = {
    SIMPLE_ROUTE_NAME: "Good for simple tasks like formatting, data extraction, and short summaries.",
    COMPLEX_ROUTE_NAME: "Good for complex tasks like reasoning, planning, coding, and generating creative text.",
}

ROUTING_PROMPT_TEMPLATE = """
Given the user's prompt, classify it as either '{simple}' or '{complex}'.

Do not respond with more than one word.

<prompt>
{{input}}
</prompt>

Classification:"""


# ... (rest of the code remains the same until get_routed_llm_config) ...

def get_routed_llm_config(prompt: str) -> tuple[str, str, str, str]:
    """
    Determines the appropriate LLM configuration based on the prompt content using a lightweight classifier.
    
    Returns (base_url, model_name, backend, model_path)
    """
    # Use ChatPromptTemplate for LCEL compatibility
    prompt_template = ChatPromptTemplate.from_template(
        ROUTING_PROMPT_TEMPLATE.format(simple=SIMPLE_ROUTE_NAME, complex=COMPLEX_ROUTE_NAME)
    )
    
    classifier_llm = LocalChatLLM(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model_name=settings.llm_model_name,
        temperature=0.0
    )

    # Use LCEL to chain the prompt, LLM, and output parser
    classifier_chain = prompt_template | classifier_llm | StrOutputParser()
    
    try:
        # Use invoke for LCEL runnables
        classification = classifier_chain.invoke({"input": prompt}).strip().upper() # Use invoke and pass dictionary for prompt
        logger.info(f"Classified prompt as: {classification}")

        if SIMPLE_ROUTE_NAME.upper() in classification:
            # Config for local/fast model (llama_cpp)
            return "", "", "llama_cpp", getattr(settings, "llama_cpp_model_path", "")
        
        # Default to complex route for safety and for any other classification
        # Config for SOTA/expensive model (OpenAI-compatible)
        return settings.llm_base_url, settings.llm_model_name, settings.llm_backend, ""

    except Exception as e:
        logger.error(f"Error during LLM classification, falling back to default: {e}")
        return settings.llm_base_url, settings.llm_model_name, settings.llm_backend, ""


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
    effective_backend = backend or settings.llm_backend.lower()
    
    if effective_backend == "llama_cpp":
        try:
            from app.services.llama_cpp_service import get_llama_cpp_service
            
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
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Local LLM API error: {e}")
        return f"LLM Error: {str(e)}"


def generate_text(
    prompt: str,
    project_id: str,
    *,
    temperature: float | None = None,
    max_tokens: int = 4096,
    json_mode: bool = False,
    image_data: Optional[str] = None,
) -> LLMResponse:
    """
    Generates text using the underlying LLM, with mode-aware adjustments and semantic routing.
    """
    if settings.cortex_mode == "INGEST":
        logger.info("Request received in INGEST mode, queuing for later processing.")
        return LLMResponse(response="Request has been queued and will be processed when ingest is complete.", status="queued")

    settings_obj: ProjectExecutionSettings = get_project_settings(project_id)
    
    base_url, model_name, backend, model_path = get_routed_llm_config(prompt)
    
    effective_temperature = settings_obj.llm_temperature if temperature is None else temperature

    logger.info(
        "llm_service.generate_text.start",
        extra={"project_id": project_id, "model": model_name, "backend": backend},
    )

    final_response = _call_underlying_llm(
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
        for i in range(settings_obj.validation_passes):
            checker_prompt = f"Review the following prompt and draft answer. Identify inconsistencies or missing steps and provide a corrected final answer.\n\nPROMPT:\n{prompt}\n\nDRAFT ANSWER:\n{final_response}"
            # Reroute for validation to ensure consistency
            val_base_url, val_model_name, val_backend, val_model_path = get_routed_llm_config(checker_prompt)
            final_response = _call_underlying_llm(
                checker_prompt,
                temperature=min(effective_temperature, 0.2),
                max_tokens=max_tokens,
                base_url=val_base_url,
                model=val_model_name,
                backend=val_backend,
                model_path=val_model_path,
            )

    # Chain of Thought might not be standard across all models.
    # Consider making this conditional on the route if needed.
    reasoning_trace = re.findall(r"<think>(.*?)</think>", final_response, re.DOTALL)
    clean_response = re.sub(r"<think>.*?</think>", "", final_response, flags=re.DOTALL).strip()
    return LLMResponse(response=clean_response, reasoning_trace=reasoning_trace or None)

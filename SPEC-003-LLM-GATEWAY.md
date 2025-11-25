Goal: Connect the backend to a real AI model.

Markdown

# SPEC-003: LLM Gateway Integration

## Problem
`llm_service.py` returns dummy text. The "Brain" is disconnected.

## Requirements
- Support **OpenAI-compatible** endpoints (allows swapping between vLLM, Ollama, or real OpenAI).
- Configurable API Key and Base URL via `app/config.py`.

## Implementation Guide

### 1. Update `backend/app/config.py`
Add:
```python
llm_base_url: str = Field("http://localhost:11434/v1", env="CORTEX_LLM_BASE_URL")
llm_api_key: str = Field("ollama", env="CORTEX_LLM_API_KEY")
llm_model_name: str = Field("llama3", env="CORTEX_LLM_MODEL")
2. Refactor backend/app/services/llm_service.py
Python

from openai import OpenAI
from app.config import get_settings

settings = get_settings()
client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

def _call_underlying_llm(
    prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    model: str = None, 
    **kwargs
) -> str:
    target_model = model or settings.llm_model_name
    
    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM Error: {str(e)}"
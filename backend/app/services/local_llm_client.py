"""
Local LLM HTTP client for OpenAI-compatible APIs (vLLM, Ollama, etc.)
Replaces OpenAI SDK with direct HTTP calls for offline-first operation.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)


class LocalLLMClient:
    """HTTP client for OpenAI-compatible local LLM APIs."""
    
    def __init__(self, base_url: str, api_key: str = "ollama"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}" if api_key else None,
                "Content-Type": "application/json",
            },
            timeout=300.0,  # 5 minutes for long-running requests
        )
    
    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion using OpenAI-compatible API.
        
        Returns a dict with 'choices' key containing list of completion objects.
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            payload["response_format"] = response_format
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        try:
            response = self.client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling LLM API: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from LLM API: {e}")
            raise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()


class LocalLLMResponse:
    """Wrapper for LLM API response to match OpenAI SDK interface."""
    
    def __init__(self, response_data: Dict[str, Any]):
        self.response_data = response_data
        self.choices = [LocalLLMChoice(choice) for choice in response_data.get("choices", [])]


class LocalLLMChoice:
    """Wrapper for choice object to match OpenAI SDK interface."""
    
    def __init__(self, choice_data: Dict[str, Any]):
        self.choice_data = choice_data
        self.message = LocalLLMMessage(choice_data.get("message", {}))


class LocalLLMMessage:
    """Wrapper for message object to match OpenAI SDK interface."""
    
    def __init__(self, message_data: Dict[str, Any]):
        self.message_data = message_data
        self.content = message_data.get("content", "")


def get_local_llm_client(base_url: Optional[str] = None, api_key: Optional[str] = None) -> LocalLLMClient:
    """
    Get a LocalLLMClient instance.
    
    This function maintains compatibility with the old OpenAI client interface.
    """
    from app.config import get_settings
    
    settings = get_settings()
    effective_base_url = base_url or settings.llm_base_url
    effective_api_key = api_key or settings.llm_api_key
    
    return LocalLLMClient(base_url=effective_base_url, api_key=effective_api_key)


class LocalChatLLM(BaseChatModel):
    """LangChain-compatible wrapper for local LLM HTTP client."""
    
    base_url: str
    api_key: str
    model_name: str
    temperature: float = 0.7
    
    @property
    def _llm_type(self) -> str:
        return "local_llm"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat completion."""
        client = get_local_llm_client(base_url=self.base_url, api_key=self.api_key)
        
        # Convert LangChain messages to API format
        api_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if msg.__class__.__name__ == 'HumanMessage':
                    api_messages.append({"role": "user", "content": msg.content})
                elif msg.__class__.__name__ == 'AIMessage':
                    api_messages.append({"role": "assistant", "content": msg.content})
                else:
                    # Default to user message
                    api_messages.append({"role": "user", "content": str(msg.content)})
        
        try:
            response = client.chat_completions_create(
                model=self.model_name,
                messages=api_messages,
                temperature=self.temperature,
                **kwargs,
            )
            
            content = response["choices"][0]["message"]["content"]
            generation = ChatGeneration(message=AIMessage(content=content))
            return ChatResult(generations=[generation])
        except Exception as e:
            logger.error(f"Error calling local LLM: {e}")
            raise


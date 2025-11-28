from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Cortex Backend")
    debug: bool = Field(default=False)
    skip_auth: bool = Field(default=False, env="CORTEX_SKIP_AUTH")
    allowed_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
        ]
    )

    atlas_db_path: str = Field(default=str(Path("atlas.db")))
    atlas_checkpoints_db_path: str = Field(default=str(Path("atlas_checkpoints.db")))

    # LLM settings
    llm_base_url: str = Field(default="http://localhost:11434/v1", env="CORTEX_LLM_BASE_URL")
    llm_api_key: str = Field(default="ollama", env="CORTEX_LLM_API_KEY")
    llm_model_name: str = Field(default="llama3", env="CORTEX_LLM_MODEL")
    
    # LLM backend selection: "openai" (vLLM/Ollama API) or "llama_cpp" (local binary)
    llm_backend: str = Field(default="openai", env="CORTEX_LLM_BACKEND")
    
    # Default lane
    llm_default_lane: str = Field(default="orchestrator", env="CORTEX_LLM_DEFAULT_LANE")
    
    # Lane-specific URLs and models
    lane_orchestrator_url: str = Field(default="", env="CORTEX_LANE_ORCHESTRATOR_URL")
    lane_orchestrator_model: str = Field(default="", env="CORTEX_LANE_ORCHESTRATOR_MODEL")
    lane_coder_url: str = Field(default="", env="CORTEX_LANE_CODER_URL")
    lane_coder_model: str = Field(default="", env="CORTEX_LANE_CODER_MODEL")
    lane_super_reader_url: str = Field(default="", env="CORTEX_LANE_SUPER_READER_URL")
    lane_super_reader_model: str = Field(default="", env="CORTEX_LANE_SUPER_READER_MODEL")
    lane_super_reader_model_path: str = Field(default="", env="CORTEX_LANE_SUPER_READER_MODEL_PATH")
    lane_coder_model_path: str = Field(default="", env="CORTEX_LANE_CODER_MODEL_PATH")
    lane_fast_rag_url: str = Field(default="", env="CORTEX_LANE_FAST_RAG_URL")
    lane_fast_rag_model: str = Field(default="", env="CORTEX_LANE_FAST_RAG_MODEL")
    lane_fast_rag_model_path: str = Field(default="", env="CORTEX_LANE_FAST_RAG_MODEL_PATH")
    lane_governance_url: str = Field(default="", env="CORTEX_LANE_GOVERNANCE_URL")
    lane_governance_model: str = Field(default="", env="CORTEX_LANE_GOVERNANCE_MODEL")
    lane_governance_model_path: str = Field(default="", env="CORTEX_LANE_GOVERNANCE_MODEL_PATH")
    
    # Optional: Per-lane backend selection (overrides auto-detection)
    lane_orchestrator_backend: str = Field(default="", env="CORTEX_LANE_ORCHESTRATOR_BACKEND")
    lane_coder_backend: str = Field(default="", env="CORTEX_LANE_CODER_BACKEND")
    lane_super_reader_backend: str = Field(default="llama_cpp", env="CORTEX_LANE_SUPER_READER_BACKEND")
    lane_fast_rag_backend: str = Field(default="", env="CORTEX_LANE_FAST_RAG_BACKEND")
    lane_governance_backend: str = Field(default="llama_cpp", env="CORTEX_LANE_GOVERNANCE_BACKEND")
    
    # llama.cpp settings (when llm_backend="llama_cpp")
    llama_cpp_binary_path: str = Field(
        default="/home/nexus/rocm/py311-tor290/bin/llama-cpp",
        env="CORTEX_LLAMA_CPP_BINARY"
    )
    llama_cpp_model_path: str = Field(
        default="",
        env="CORTEX_LLAMA_CPP_MODEL_PATH"
    )
    llama_cpp_n_ctx: int = Field(default=4096, env="CORTEX_LLAMA_CPP_N_CTX")  # Context window size (can be up to 4M for ultra-long context)
    llama_cpp_n_threads: int = Field(default=4, env="CORTEX_LLAMA_CPP_N_THREADS")  # CPU threads
    llama_cpp_n_gpu_layers: int = Field(default=99, env="CORTEX_LLAMA_CPP_N_GPU_LAYERS")  # GPU layers (99 = all layers for ROCm)

    # --- Execution mode defaults ---
    normal_mode_llm_temperature: float = Field(0.2, env="CORTEX_NORMAL_TEMP")
    normal_mode_validation_passes: int = Field(1, env="CORTEX_NORMAL_VALIDATION_PASSES")
    normal_mode_max_parallel_tools: int = Field(8, env="CORTEX_NORMAL_MAX_PARALLEL_TOOLS")

    # Paranoid mode: slower, more redundancy & cross-checks.
    paranoid_mode_llm_temperature: float = Field(0.1, env="CORTEX_PARANOID_TEMP")
    paranoid_mode_validation_passes: int = Field(3, env="CORTEX_PARANOID_VALIDATION_PASSES")
    paranoid_mode_max_parallel_tools: int = Field(3, env="CORTEX_PARANOID_MAX_PARALLEL_TOOLS")

    auth_secret: str = Field(default="a_very_secret_key", env="CORTEX_AUTH_SECRET")

    # Qdrant settings
    qdrant_url: str = Field(default="http://localhost:6333", env="CORTEX_QDRANT_URL")

    # n8n settings
    n8n_base_url: str = Field(default="http://localhost:5678", env="CORTEX_N8N_BASE_URL")
    n8n_api_key: str = Field(default="", env="CORTEX_N8N_API_KEY")
    n8n_webhook_timeout: int = Field(default=300, env="CORTEX_N8N_WEBHOOK_TIMEOUT")  # 5 minutes default
    n8n_max_retries: int = Field(default=3, env="CORTEX_N8N_MAX_RETRIES")
    n8n_retry_delay: float = Field(default=1.0, env="CORTEX_N8N_RETRY_DELAY")  # seconds

    # Hugging Face token for authenticated model downloads (optional, for private/gated models)
    # Note: huggingface-hub and sentence-transformers automatically use HF_TOKEN from environment
    hf_token: str = Field(default="", env="HF_TOKEN")

    model_config = SettingsConfigDict(env_prefix="CORTEX_", env_file=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

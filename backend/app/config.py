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
            "http://127.0.0.1:5173",
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
    
    # llama.cpp settings (when llm_backend="llama_cpp")
    llama_cpp_binary_path: str = Field(
        default="/home/nexus/rocm/py311-tor290/bin/llama-cpp",
        env="CORTEX_LLAMA_CPP_BINARY"
    )
    llama_cpp_model_path: str = Field(
        default="",
        env="CORTEX_LLAMA_CPP_MODEL_PATH"
    )
    llama_cpp_n_ctx: int = Field(default=4096, env="CORTEX_LLAMA_CPP_N_CTX")  # Context window size
    llama_cpp_n_threads: int = Field(default=4, env="CORTEX_LLAMA_CPP_N_THREADS")  # CPU threads

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

    model_config = SettingsConfigDict(env_prefix="CORTEX_", env_file=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

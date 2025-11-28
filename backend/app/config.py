import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CortexMode = Literal["PARALLEL", "INGEST"]
CortexEnv = Literal["local", "strix", "production"]


class Settings(BaseSettings):
    app_name: str = Field(default="Cortex Backend")
    debug: bool = Field(default=False)
    skip_auth: bool = Field(default=False, env="CORTEX_SKIP_AUTH")
    auth_secret: Optional[str] = Field(default=None, env="CORTEX_AUTH_SECRET")

    # Environment variable for allowed origins, comma-separated
    allowed_origins_str: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173",
        env="CORTEX_ALLOWED_ORIGINS",
    )

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_str.split(",")]

    database_url: str = Field(default="sqlite:///atlas.db", env="CORTEX_DATABASE_URL")
    atlas_db_path: str = Field(default=str(Path("atlas.db")), env="CORTEX_ATLAS_DB_PATH")
    atlas_checkpoints_db_path: str = Field(default=str(Path("atlas_checkpoints.db")), env="CORTEX_ATLAS_CHECKPOINTS_DB_PATH")
    qdrant_url: str = Field(default="http://localhost:6333", env="CORTEX_QDRANT_URL")
    n8n_base_url: str = Field(default="http://localhost:5678", env="CORTEX_N8N_BASE_URL")
    n8n_api_key: str = Field(default="", env="CORTEX_N8N_API_KEY")

    # --- Core Settings ---
    cortex_mode: CortexMode = Field(default="PARALLEL", env="CORTEX_MODE")
    cortex_env: CortexEnv = Field(default="local", env="CORTEX_ENV")

    # --- Mode defaults for LLM execution and validation passes ---
    normal_mode_llm_temperature: float = Field(default=0.3, env="CORTEX_NORMAL_MODE_LLM_TEMPERATURE")
    normal_mode_validation_passes: int = Field(default=1, env="CORTEX_NORMAL_MODE_VALIDATION_PASSES")
    normal_mode_max_parallel_tools: int = Field(default=8, env="CORTEX_NORMAL_MODE_MAX_PARALLEL_TOOLS")

    paranoid_mode_llm_temperature: float = Field(default=0.2, env="CORTEX_PARANOID_MODE_LLM_TEMPERATURE")
    paranoid_mode_validation_passes: int = Field(default=2, env="CORTEX_PARANOID_MODE_VALIDATION_PASSES")
    paranoid_mode_max_parallel_tools: int = Field(default=4, env="CORTEX_PARANOID_MODE_MAX_PARALLEL_TOOLS")

    # --- LLM Settings ---
    llm_backend: str = Field(default="llama_cpp", env="CORTEX_LLM_BACKEND")
    llm_base_url: str = Field(default="http://localhost:11434/v1", env="CORTEX_LLM_BASE_URL")
    llm_api_key: str = Field(default="ollama", env="CORTEX_LLM_API_KEY")
    llm_model_name: str = Field(default="llama3", env="CORTEX_LLM_MODEL")
    llm_default_lane: str = Field(default="orchestrator", env="CORTEX_LLM_DEFAULT_LANE")
    llama_cpp_binary_path: str = Field(
        default="~/rocm/py311-tor290/bin/llama-cpp-tuned",
        env="CORTEX_LLAMA_CPP_BINARY_PATH",
    )
    llama_quantize_binary_path: str = Field(
        default="~/rocm/py311-tor290/bin/llama-quantize-tuned",
        env="CORTEX_LLAMA_QUANTIZE_BINARY_PATH",
    )

    # --- Lane Settings ---
    lane_super_reader_url: str = Field(
        default="http://localhost:8080/v1", env="CORTEX_LANE_SUPER_READER_URL"
    )
    lane_super_reader_model: str = Field(default="Nemotron-8B-UltraLong-4M", env="CORTEX_LANE_SUPER_READER_MODEL")
    lane_super_reader_model_path: str = Field(default="", env="CORTEX_LANE_SUPER_READER_MODEL_PATH")
    lane_super_reader_backend: str = Field(default="llama_cpp", env="CORTEX_LANE_SUPER_READER_BACKEND")

    lane_orchestrator_url: str = Field(default="http://localhost:8000/v1", env="CORTEX_LANE_ORCHESTRATOR_URL")
    lane_orchestrator_model: str = Field(default="Qwen3-30B-Thinking", env="CORTEX_LANE_ORCHESTRATOR_MODEL")
    lane_orchestrator_model_path: str = Field(default="", env="CORTEX_LANE_ORCHESTRATOR_MODEL_PATH")
    lane_orchestrator_backend: str = Field(default="", env="CORTEX_LANE_ORCHESTRATOR_BACKEND")

    lane_coder_url: str = Field(default="http://localhost:8000/v1", env="CORTEX_LANE_CODER_URL")
    lane_coder_model: str = Field(default="Qwen3-Coder-30B-1M", env="CORTEX_LANE_CODER_MODEL")
    lane_coder_model_path: str = Field(default="", env="CORTEX_LANE_CODER_MODEL_PATH")
    lane_coder_backend: str = Field(default="", env="CORTEX_LANE_CODER_BACKEND")

    lane_fast_rag_url: str = Field(default="http://localhost:8000/v1", env="CORTEX_LANE_FAST_RAG_URL")
    lane_fast_rag_model: str = Field(default="MegaBeam-Mistral-7B-512k", env="CORTEX_LANE_FAST_RAG_MODEL")
    lane_fast_rag_model_path: str = Field(default="", env="CORTEX_LANE_FAST_RAG_MODEL_PATH")
    lane_fast_rag_backend: str = Field(default="", env="CORTEX_LANE_FAST_RAG_BACKEND")

    lane_governance_url: str = Field(default="http://localhost:8080/v1", env="CORTEX_LANE_GOVERNANCE_URL")
    lane_governance_model: str = Field(default="Granite-4.x-Long-Context", env="CORTEX_LANE_GOVERNANCE_MODEL")
    lane_governance_model_path: str = Field(default="", env="CORTEX_LANE_GOVERNANCE_MODEL_PATH")
    lane_governance_backend: str = Field(default="llama_cpp", env="CORTEX_LANE_GOVERNANCE_BACKEND")
    # lane_orchestrator_url already defined above

    @model_validator(mode="after")
    def set_strix_defaults(self) -> "Settings":
        if self.cortex_env in ["strix", "production"]:
            self.database_url = "postgresql://cortex:cortex@localhost:5432/cortex"
        if self.cortex_env == "strix":
            self.llm_backend = "openai"
            # The following lines are already defaulted to the correct values for strix
            # self.lane_super_reader_url = "http://localhost:8080/v1"
            # self.lane_orchestrator_url = "http://localhost:8000/v1"

        # Validate auth secret
        if not self.auth_secret:
            if self.cortex_env == "local":
                self.auth_secret = secrets.token_hex(32)
            else:
                raise ValueError(
                    "CORTEX_AUTH_SECRET must be set in strix or production environment"
                )
        # During local development and testing, default to skipping auth for convenience
        if self.cortex_env == "local":
            self.skip_auth = True
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
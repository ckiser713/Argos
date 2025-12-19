import logging
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

ArgosMode = Literal["PARALLEL", "INGEST"]
ArgosEnv = Literal["local", "strix", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")
    
    app_name: str = Field(default="Argos Backend")
    debug: bool = Field(default=False)
    skip_auth: bool = Field(default=False, env="ARGOS_SKIP_AUTH")
    auth_secret: Optional[str] = Field(default=None, env="ARGOS_AUTH_SECRET")
    access_token_minutes: int = Field(default=15, env="ARGOS_ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=7, env="ARGOS_REFRESH_TOKEN_DAYS")
    log_level: str = Field(default="INFO", env="ARGOS_LOG_LEVEL")
    log_json: bool = Field(default=True, env="ARGOS_LOG_JSON")
    enable_tracing: bool = Field(default=False, env="ARGOS_ENABLE_TRACING")
    otel_exporter_endpoint: Optional[str] = Field(default=None, env="ARGOS_OTEL_EXPORTER_ENDPOINT")
    otel_service_name: str = Field(default="argos-backend", env="ARGOS_OTEL_SERVICE_NAME")
    otel_sample_ratio: float = Field(default=1.0, env="ARGOS_OTEL_SAMPLE_RATIO")

    # Environment variable for allowed origins, comma-separated
    allowed_origins_str: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173",
        env="ARGOS_ALLOWED_ORIGINS",
    )

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_str.split(",")]

    database_url: str = Field(default="sqlite:///atlas.db", env="ARGOS_DATABASE_URL")
    atlas_db_path: str = Field(default=str(Path("atlas.db")), env="ARGOS_ATLAS_DB_PATH")
    atlas_checkpoints_db_path: str = Field(default=str(Path("atlas_checkpoints.db")), env="ARGOS_ATLAS_CHECKPOINTS_DB_PATH")
    qdrant_url: str = Field(default="http://localhost:6333", env="ARGOS_QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="ARGOS_QDRANT_API_KEY")
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", env="ARGOS_EMBEDDING_MODEL_NAME")
    code_embedding_model_name: Optional[str] = Field(
        default="jinaai/jina-embeddings-v2-base-code", env="ARGOS_CODE_EMBEDDING_MODEL_NAME"
    )
    embedding_device: str = Field(
        default="auto",
        env="ARGOS_EMBEDDING_DEVICE",
        description="Preferred embedding device: auto|cpu|cuda|rocm",
    )
    require_embeddings: bool = Field(default=False, env="ARGOS_REQUIRE_EMBEDDINGS")
    n8n_base_url: str = Field(default="http://localhost:5678", env="ARGOS_N8N_BASE_URL")
    n8n_api_key: str = Field(default="", env="ARGOS_N8N_API_KEY")

    # --- Core Settings ---
    argos_mode: ArgosMode = Field(default="PARALLEL", env="ARGOS_MODE")
    argos_env: ArgosEnv = Field(default="local", env="ARGOS_ENV")

    # --- Mode defaults for LLM execution and validation passes ---
    normal_mode_llm_temperature: float = Field(default=0.2, env="ARGOS_NORMAL_MODE_LLM_TEMPERATURE")
    normal_mode_validation_passes: int = Field(default=1, env="ARGOS_NORMAL_MODE_VALIDATION_PASSES")
    normal_mode_max_parallel_tools: int = Field(default=8, env="ARGOS_NORMAL_MODE_MAX_PARALLEL_TOOLS")

    paranoid_mode_llm_temperature: float = Field(default=0.2, env="ARGOS_PARANOID_MODE_LLM_TEMPERATURE")
    paranoid_mode_validation_passes: int = Field(default=2, env="ARGOS_PARANOID_MODE_VALIDATION_PASSES")
    paranoid_mode_max_parallel_tools: int = Field(default=4, env="ARGOS_PARANOID_MODE_MAX_PARALLEL_TOOLS")

    # --- LLM Settings ---
    llm_backend: str = Field(default="llama_cpp", env="ARGOS_LLM_BACKEND")
    llm_base_url: str = Field(default="http://localhost:11434/v1", env="ARGOS_LLM_BASE_URL")
    llm_api_key: str = Field(default="ollama", env="ARGOS_LLM_API_KEY")
    llm_model_name: str = Field(default="llama3", env="ARGOS_LLM_MODEL")
    llm_default_lane: str = Field(default="orchestrator", env="ARGOS_LLM_DEFAULT_LANE")
    llama_cpp_binary_path: str = Field(
        default="~/rocm/py311-tor290/bin/llama-cpp-tuned",
        env="ARGOS_LLAMA_CPP_BINARY_PATH",
    )
    llama_quantize_binary_path: str = Field(
        default="~/rocm/py311-tor290/bin/llama-quantize-tuned",
        env="ARGOS_LLAMA_QUANTIZE_BINARY_PATH",
    )
    llama_cpp_model_path: str = Field(
        default="",
        env="ARGOS_LLAMA_CPP_MODEL_PATH",
    )
    llama_cpp_n_ctx: int = Field(
        default=4096,
        env="ARGOS_LLAMA_CPP_N_CTX",
    )
    llama_cpp_n_threads: int = Field(
        default=8,
        env="ARGOS_LLAMA_CPP_N_THREADS",
    )
    llama_cpp_n_gpu_layers: int = Field(
        default=99,
        env="ARGOS_LLAMA_CPP_N_GPU_LAYERS",
    )

    # --- Lane Settings ---
    lane_super_reader_url: str = Field(
        default="http://localhost:8080/v1", env="ARGOS_LANE_SUPER_READER_URL"
    )
    lane_super_reader_model: str = Field(default="Nemotron-8B-UltraLong-4M", env="ARGOS_LANE_SUPER_READER_MODEL")
    lane_super_reader_model_path: str = Field(default="", env="ARGOS_LANE_SUPER_READER_MODEL_PATH")
    lane_super_reader_backend: str = Field(default="llama_cpp", env="ARGOS_LANE_SUPER_READER_BACKEND")

    lane_orchestrator_url: str = Field(default="http://localhost:8000/v1", env="ARGOS_LANE_ORCHESTRATOR_URL")
    lane_orchestrator_model: str = Field(default="Qwen3-30B-Thinking", env="ARGOS_LANE_ORCHESTRATOR_MODEL")
    lane_orchestrator_model_path: str = Field(default="", env="ARGOS_LANE_ORCHESTRATOR_MODEL_PATH")
    lane_orchestrator_backend: str = Field(default="", env="ARGOS_LANE_ORCHESTRATOR_BACKEND")

    lane_coder_url: str = Field(default="http://localhost:8000/v1", env="ARGOS_LANE_CODER_URL")
    lane_coder_model: str = Field(default="Qwen3-Coder-30B-1M", env="ARGOS_LANE_CODER_MODEL")
    lane_coder_model_path: str = Field(default="", env="ARGOS_LANE_CODER_MODEL_PATH")
    lane_coder_backend: str = Field(default="", env="ARGOS_LANE_CODER_BACKEND")

    lane_fast_rag_url: str = Field(default="http://localhost:8000/v1", env="ARGOS_LANE_FAST_RAG_URL")
    lane_fast_rag_model: str = Field(default="MegaBeam-Mistral-7B-512k", env="ARGOS_LANE_FAST_RAG_MODEL")
    lane_fast_rag_model_path: str = Field(default="", env="ARGOS_LANE_FAST_RAG_MODEL_PATH")
    lane_fast_rag_backend: str = Field(default="", env="ARGOS_LANE_FAST_RAG_BACKEND")

    # --- Storage Settings ---
    storage_backend: Literal["s3", "local"] = Field(default="local", env="ARGOS_STORAGE_BACKEND")
    storage_bucket: str = Field(default="argos-ingest", env="ARGOS_STORAGE_BUCKET")
    storage_endpoint_url: Optional[str] = Field(default=None, env="ARGOS_STORAGE_ENDPOINT_URL")
    storage_region: Optional[str] = Field(default="us-east-1", env="ARGOS_STORAGE_REGION")
    storage_access_key: Optional[str] = Field(default=None, env="ARGOS_STORAGE_ACCESS_KEY")
    storage_secret_key: Optional[str] = Field(default=None, env="ARGOS_STORAGE_SECRET_KEY")
    storage_secure: bool = Field(default=True, env="ARGOS_STORAGE_SECURE")
    storage_prefix: str = Field(default="ingest", env="ARGOS_STORAGE_PREFIX")
    storage_local_dir: str = Field(default=str(Path("storage_uploads")), env="ARGOS_STORAGE_LOCAL_DIR")
    storage_max_upload_mb: int = Field(default=128, env="ARGOS_STORAGE_MAX_UPLOAD_MB")
    storage_allowed_content_types: str = Field(
        default="text/plain,application/pdf,application/json",
        env="ARGOS_STORAGE_ALLOWED_CONTENT_TYPES",
    )

    @property
    def storage_allowed_types(self) -> List[str]:
        return [ct.strip().lower() for ct in self.storage_allowed_content_types.split(",") if ct.strip()]

    # --- Task Queue Settings ---
    celery_broker_url: str = Field(default="redis://redis:6379/0", env="ARGOS_CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(default="redis://redis:6379/0", env="ARGOS_CELERY_RESULT_BACKEND")
    tasks_eager: bool = Field(default=True, env="ARGOS_TASKS_EAGER")
    task_max_retries: int = Field(default=3, env="ARGOS_TASK_MAX_RETRIES")
    task_retry_backoff_seconds: int = Field(default=5, env="ARGOS_TASK_RETRY_BACKOFF_SECONDS")
    task_retry_backoff_max_seconds: int = Field(default=300, env="ARGOS_TASK_RETRY_BACKOFF_MAX_SECONDS")

    lane_governance_url: str = Field(default="http://localhost:8081/v1", env="ARGOS_LANE_GOVERNANCE_URL")
    lane_governance_model: str = Field(default="Granite-4.x-Long-Context", env="ARGOS_LANE_GOVERNANCE_MODEL")
    lane_governance_model_path: str = Field(default="", env="ARGOS_LANE_GOVERNANCE_MODEL_PATH")
    lane_governance_backend: str = Field(default="llama_cpp", env="ARGOS_LANE_GOVERNANCE_BACKEND")
    # lane_orchestrator_url already defined above

    @model_validator(mode="after")
    def set_strix_defaults(self) -> "Settings":
        db_url = (self.database_url or "").strip()
        # Disallow legacy env var naming to avoid silent misconfiguration
        if os.environ.get("ARGOS_DB_URL") and not os.environ.get("ARGOS_DATABASE_URL"):
            raise ValueError("ARGOS_DB_URL is deprecated; use ARGOS_DATABASE_URL with a Postgres URL.")

        if self.argos_env != "local":
            normalized = db_url.lower()
            if not db_url:
                raise ValueError("ARGOS_DATABASE_URL must be set to a Postgres URL when ARGOS_ENV is not local.")
            if "sqlite" in normalized:
                raise ValueError("SQLite is only supported for local development. Provide a Postgres ARGOS_DATABASE_URL.")
            if not normalized.startswith("postgresql"):
                raise ValueError("ARGOS_DATABASE_URL must start with 'postgresql://' for non-local environments.")
        else:
            if not db_url:
                self.database_url = "sqlite:///atlas.db"

        allow_local_storage = str(os.environ.get("ARGOS_ALLOW_LOCAL_STORAGE", "")).strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

        if self.argos_env in ["strix", "production"]:
            # Update lane URLs to use Docker service names when not explicitly set
            if not os.environ.get("ARGOS_LANE_SUPER_READER_URL"):
                self.lane_super_reader_url = "http://llama-super-reader:8080/v1"
            if not os.environ.get("ARGOS_LANE_GOVERNANCE_URL"):
                self.lane_governance_url = "http://llama-governance:8081/v1"
            if not os.environ.get("ARGOS_LANE_ORCHESTRATOR_URL"):
                self.lane_orchestrator_url = "http://inference-vllm:8000/v1"
            if not os.environ.get("ARGOS_LANE_CODER_URL"):
                self.lane_coder_url = "http://inference-vllm:8000/v1"
            if not os.environ.get("ARGOS_LANE_FAST_RAG_URL"):
                self.lane_fast_rag_url = "http://inference-vllm:8000/v1"
            if not os.environ.get("ARGOS_QDRANT_URL"):
                self.qdrant_url = "http://qdrant:6333"
            if not os.environ.get("ARGOS_REQUIRE_EMBEDDINGS"):
                # Enforce embeddings in non-local environments unless explicitly overridden
                self.require_embeddings = True
                
        if self.argos_env == "strix":
            self.llm_backend = "local_http"  # Use local HTTP client instead of OpenAI
            # The following lines are already defaulted to the correct values for strix
            # self.lane_super_reader_url = "http://localhost:8080/v1"
            # self.lane_orchestrator_url = "http://localhost:8000/v1"

        # Validate auth secret
        # Check environment variable directly if auth_secret is None (Pydantic may not read it)
        env_auth_secret = os.environ.get("ARGOS_AUTH_SECRET")
        if not self.auth_secret and env_auth_secret:
            self.auth_secret = env_auth_secret

        weak_secrets = {
            "secret",
            "changeme",
            "password",
            "admin",
            "argos",
            "dev",
            "test",
            "local",
        }

        if self.argos_env != "local":
            if not self.auth_secret:
                raise ValueError(
                    "ARGOS_AUTH_SECRET must be set in strix or production environment"
                )
            normalized_secret = self.auth_secret.strip().lower()
            if len(self.auth_secret) < 32 or normalized_secret in weak_secrets:
                raise ValueError(
                    "ARGOS_AUTH_SECRET is too weak for non-local environments; use a random 32+ character secret."
                )
            # Auth must remain enabled outside local
            self.skip_auth = False
            # Queue must run out-of-process in non-local environments
            self.tasks_eager = False
            if self.storage_backend == "local":
                if not allow_local_storage:
                    raise ValueError(
                        "Local storage in non-local environments requires ARGOS_ALLOW_LOCAL_STORAGE=1 "
                        "or set ARGOS_STORAGE_BACKEND=s3 with credentials."
                    )
                logger.warning(
                    "ARGOS_STORAGE_BACKEND=local in non-local environment; ensure durable volume and backups."
                )
        else:
            if not self.auth_secret:
                self.auth_secret = secrets.token_hex(32)
            elif len(self.auth_secret) < 16 or self.auth_secret.strip().lower() in weak_secrets:
                logger.warning(
                    "ARGOS_AUTH_SECRET looks weak; set a stronger value even for local development."
                )
            # During local development and testing, default to skipping auth unless explicitly overridden
            if os.environ.get("ARGOS_SKIP_AUTH") is None:
                self.skip_auth = True
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
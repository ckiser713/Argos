from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CortexMode = Literal["PARALLEL", "INGEST"]
CortexEnv = Literal["local", "strix", "production"]


class Settings(BaseSettings):
    app_name: str = Field(default="Cortex Backend")
    debug: bool = Field(default=False)
    skip_auth: bool = Field(default=False, env="CORTEX_SKIP_AUTH")
    
    # Environment variable for allowed origins, comma-separated
    allowed_origins_str: str = Field(default="http://localhost:5173,http://127.0.0.1:5173,http://0.0.0.0:5173", env="CORTEX_ALLOWED_ORIGINS")
    
    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_str.split(',')]

    database_url: str = Field(default="sqlite:///atlas.db", env="CORTEX_DATABASE_URL")

    # --- Core Settings ---
    cortex_mode: CortexMode = Field(default="PARALLEL", env="CORTEX_MODE")
    cortex_env: CortexEnv = Field(default="local", env="CORTEX_ENV")

    # --- LLM Settings ---
    llm_backend: str = Field(default="llama_cpp", env="CORTEX_LLM_BACKEND")
    llama_cpp_binary_path: str = Field(default="~/rocm/py311-tor290/bin/llama-cpp-tuned", env="CORTEX_LLAMA_CPP_BINARY_PATH")
    llama_quantize_binary_path: str = Field(default="~/rocm/py311-tor290/bin/llama-quantize-tuned", env="CORTEX_LLAMA_QUANTIZE_BINARY_PATH")
    
    # --- Lane Settings ---
    lane_super_reader_url: str = Field(default="http://localhost:8080/v1", env="CORTEX_LANE_SUPER_READER_URL")
    lane_orchestrator_url: str = Field(default="http://localhost:8000/v1", env="CORTEX_LANE_ORCHESTRATOR_URL")

    @model_validator(mode='after')
    def set_strix_defaults(self) -> 'Settings':
        if self.cortex_env in ['strix', 'production']:
            self.database_url = "postgresql://cortex:cortex@localhost:5432/cortex"
        if self.cortex_env == 'strix':
            self.llm_backend = 'openai'
            # The following lines are already defaulted to the correct values for strix
            # self.lane_super_reader_url = "http://localhost:8080/v1"
            # self.lane_orchestrator_url = "http://localhost:8000/v1"
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
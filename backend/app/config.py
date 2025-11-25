from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ... your existing fields ...

    app_name: str = Field(default="Cortex Backend")
    debug: bool = Field(default=False)
    allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    )

    # --- Execution mode defaults ---
    # Normal mode: faster, less redundant.
    normal_mode_llm_temperature: float = Field(0.2, env="CORTEX_NORMAL_TEMP")
    normal_mode_validation_passes: int = Field(1, env="CORTEX_NORMAL_VALIDATION_PASSES")
    normal_mode_max_parallel_tools: int = Field(8, env="CORTEX_NORMAL_MAX_PARALLEL_TOOLS")


    # Paranoid mode: slower, more redundancy & cross-checks.
    paranoid_mode_llm_temperature: float = Field(0.1, env="CORTEX_PARANOID_TEMP")
    paranoid_mode_validation_passes: int = Field(3, env="CORTEX_PARANOID_VALIDATION_PASSES")
    paranoid_mode_max_parallel_tools: int = Field(3, env="CORTEX_PARANOID_MAX_PARALLEL_TOOLS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

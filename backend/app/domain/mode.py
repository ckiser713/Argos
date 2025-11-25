from __future__ import annotations


from typing import Literal


from pydantic import BaseModel, Field




ExecutionMode = Literal["normal", "paranoid"]




class ProjectExecutionSettings(BaseModel):
    """Per-project execution behavior.


    These settings are intended to be lightweight and read on every agent / LLM call,
    so they should remain small and fast to validate.
    """


    project_id: str = Field(..., description="Logical project identifier")
    mode: ExecutionMode = Field(
        "normal",
        description="Execution mode: 'normal' for fast single-pass, 'paranoid' for extra validation",
    )


    # LLM tuning
    llm_temperature: float = Field(
        0.2,
        ge=0.0,
        le=2.0,
        description="Base temperature used for this project's LLM calls",
    )


    # How many validation / cross-check passes should be attempted for critical operations.
    validation_passes: int = Field(
        1,
        ge=1,
        le=10,
        description="Number of validation / checker passes on critical flows",
    )


    # Clamp parallelism for tools / sub-agents to avoid over-fanout in paranoid mode.
    max_parallel_tools: int = Field(
        4,
        ge=1,
        le=64,
        description="Maximum parallel tools/subtasks for this project",
    )

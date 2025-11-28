from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class GpuMetrics(BaseModel):
    """Best-effort GPU metrics; fields may be None if unavailable."""

    name: Optional[str] = Field(
        default=None,
        description="GPU name/model, if detectable (e.g., 'AMD Radeon RX 7900 XTX').",
    )
    total_vram_gb: Optional[float] = Field(default=None, description="Total VRAM in GiB, if detectable.")
    used_vram_gb: Optional[float] = Field(default=None, description="Used VRAM in GiB, if detectable.")
    utilization_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="GPU utilization percentage.")


class CpuMetrics(BaseModel):
    """Logical CPU load snapshot."""

    num_cores: int = Field(..., ge=1, description="Number of logical CPU cores detected.")
    load_pct: float = Field(..., ge=0.0, le=100.0, description="Overall CPU utilization percentage.")


class MemoryMetrics(BaseModel):
    """System memory metrics in GiB."""

    total_gb: float = Field(..., gt=0.0, description="Total system RAM in GiB.")
    used_gb: float = Field(..., ge=0.0, description="Used RAM in GiB (total - available).")


class ContextMetrics(BaseModel):
    """Logical token-budget view for the Cortex runtime."""

    total_tokens: int = Field(..., ge=0, description="Total token budget.")
    used_tokens: int = Field(..., ge=0, description="Tokens currently consumed.")


SystemStatusLiteral = Literal["nominal", "warning", "critical", "warming_up"]


class SystemStatus(BaseModel):
    """Aggregated view for the Command Center header."""

    status: SystemStatusLiteral = Field(
        ...,
        description="Overall system status derived from CPU, memory, GPU, and context usage.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Human-readable summary of why the status is non-nominal, if applicable.",
    )
    gpu: Optional[GpuMetrics] = Field(
        default=None,
        description="GPU metrics, or None if no ROCm-capable device is visible.",
    )
    cpu: CpuMetrics
    memory: MemoryMetrics
    context: ContextMetrics
    active_agent_runs: int = Field(..., ge=0, description="Number of currently active agent runs.")

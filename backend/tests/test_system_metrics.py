from __future__ import annotations

from typing import Optional

import pytest

from app.domain.system_metrics import (
    ContextMetrics,
    CpuMetrics,
    GpuMetrics,
    MemoryMetrics,
    SystemStatus,
)
from app.services import system_metrics_service as svc


class DummyGpu:
    @staticmethod
    def make(
        name: Optional[str] = "AMD Test GPU",
        total_vram_gb: Optional[float] = 16.0,
        used_vram_gb: Optional[float] = 4.0,
        utilization_pct: Optional[float] = 25.0,
    ) -> GpuMetrics:
        return GpuMetrics(
            name=name,
            total_vram_gb=total_vram_gb,
            used_vram_gb=used_vram_gb,
            utilization_pct=utilization_pct,
        )


def test_system_status_nominal(monkeypatch: pytest.MonkeyPatch) -> None:
    """All metrics in a low range should yield 'nominal' with no reason string."""

    def fake_gpu() -> Optional[GpuMetrics]:
        return DummyGpu.make()

    def fake_cpu() -> CpuMetrics:
        return CpuMetrics(num_cores=16, load_pct=30.0)

    def fake_mem() -> MemoryMetrics:
        return MemoryMetrics(total_gb=64.0, used_gb=16.0)

    def fake_ctx() -> ContextMetrics:
        return ContextMetrics(total_tokens=1_000_000, used_tokens=100_000)

    def fake_active_runs() -> int:
        return 2

    monkeypatch.setattr(svc, "get_gpu_metrics", fake_gpu)
    monkeypatch.setattr(svc, "get_cpu_metrics", fake_cpu)
    monkeypatch.setattr(svc, "get_memory_metrics", fake_mem)
    monkeypatch.setattr(svc, "get_context_metrics", fake_ctx)
    monkeypatch.setattr(svc, "_get_active_agent_runs", fake_active_runs)

    status: SystemStatus = svc.get_system_status()

    assert status.status == "nominal"
    assert status.reason is None
    assert status.active_agent_runs == 2
    assert status.cpu.load_pct == 30.0
    assert status.memory.used_gb == 16.0
    assert status.context.used_tokens == 100_000


def test_system_status_warning_for_cpu_and_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elevated CPU and memory usage should produce a 'warning' status."""
    monkeypatch.setattr(svc, "get_gpu_metrics", lambda: None)

    def fake_cpu() -> CpuMetrics:
        return CpuMetrics(num_cores=8, load_pct=80.0)

    def fake_mem() -> MemoryMetrics:
        # 80% utilization
        return MemoryMetrics(total_gb=32.0, used_gb=25.6)

    def fake_ctx() -> ContextMetrics:
        # Low context usage
        return ContextMetrics(total_tokens=1_000_000, used_tokens=100_000)

    monkeypatch.setattr(svc, "get_cpu_metrics", fake_cpu)
    monkeypatch.setattr(svc, "get_memory_metrics", fake_mem)
    monkeypatch.setattr(svc, "get_context_metrics", fake_ctx)
    monkeypatch.setattr(svc, "_get_active_agent_runs", lambda: 1)

    status: SystemStatus = svc.get_system_status()

    assert status.status == "warning"
    assert status.reason is not None
    # Should mention at least CPU or memory in the reason.
    assert "CPU load" in status.reason or "Memory usage" in status.reason


def test_system_status_critical_for_gpu_or_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    High GPU utilization or nearly exhausted context budget should drive a critical status.
    We'll simulate both being high to ensure 'critical' dominates.
    """

    def fake_gpu() -> Optional[GpuMetrics]:
        # 95% utilization and 95% VRAM usage
        return DummyGpu.make(total_vram_gb=16.0, used_vram_gb=15.2, utilization_pct=95.0)

    def fake_cpu() -> CpuMetrics:
        # Modest CPU load
        return CpuMetrics(num_cores=16, load_pct=40.0)

    def fake_mem() -> MemoryMetrics:
        # Modest memory usage
        return MemoryMetrics(total_gb=64.0, used_gb=32.0)

    def fake_ctx() -> ContextMetrics:
        # 97% context budget used
        return ContextMetrics(total_tokens=1_000_000, used_tokens=970_000)

    monkeypatch.setattr(svc, "get_gpu_metrics", fake_gpu)
    monkeypatch.setattr(svc, "get_cpu_metrics", fake_cpu)
    monkeypatch.setattr(svc, "get_memory_metrics", fake_mem)
    monkeypatch.setattr(svc, "get_context_metrics", fake_ctx)
    monkeypatch.setattr(svc, "_get_active_agent_runs", lambda: 3)

    status: SystemStatus = svc.get_system_status()

    assert status.status == "critical"
    assert status.reason is not None
    # Reason should reference GPU and/or context exhaustion.
    assert ("GPU" in status.reason) or ("Context budget" in status.reason)


def test_system_status_handles_missing_gpu_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """If GPU metrics are unavailable, status should still classify based on CPU/memory/context."""
    monkeypatch.setattr(svc, "get_gpu_metrics", lambda: None)

    def fake_cpu() -> CpuMetrics:
        return CpuMetrics(num_cores=8, load_pct=10.0)

    def fake_mem() -> MemoryMetrics:
        return MemoryMetrics(total_gb=32.0, used_gb=4.0)

    def fake_ctx() -> ContextMetrics:
        return ContextMetrics(total_tokens=1_000_000, used_tokens=100_000)

    monkeypatch.setattr(svc, "get_cpu_metrics", fake_cpu)
    monkeypatch.setattr(svc, "get_memory_metrics", fake_mem)
    monkeypatch.setattr(svc, "get_context_metrics", fake_ctx)
    monkeypatch.setattr(svc, "_get_active_agent_runs", lambda: 0)

    status: SystemStatus = svc.get_system_status()

    assert status.status == "nominal"
    assert status.gpu is None

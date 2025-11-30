from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

try:
    import psutil  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercise via monkeypatching in tests
    psutil = None  # type: ignore[assignment]

from app.domain.system_metrics import (
    ContextMetrics,
    CpuMetrics,
    GpuMetrics,
    MemoryMetrics,
    SystemStatus,
    SystemStatusLiteral,
)
from app.services.model_warmup_service import model_warmup_service

# ---------------------------------------------------------------------------
# Config / stubs
# ---------------------------------------------------------------------------

# Fallback context budget if app.config.settings is not available.
_DEFAULT_CONTEXT_TOTAL_TOKENS = 8_000_000

try:
    # Optional: if you have app.config with Settings, wire context config here.
    from app.config import get_settings  # Adjusted to use get_settings

    settings = get_settings()
except ImportError:  # pragma: no cover - configuration not available in tests
    settings = None  # type: ignore[assignment]


def _get_configured_context_total_tokens() -> int:
    if settings is not None and hasattr(settings, "context_total_tokens"):
        return int(getattr(settings, "context_total_tokens"))
    return _DEFAULT_CONTEXT_TOTAL_TOKENS


# Simple module-level stub for used tokens / active runs.
# In a real system, these would be driven by an agent manager / context manager.
_context_used_tokens: int = 0
_active_agent_runs_stub: int = 0


def set_context_usage_stub(used_tokens: int) -> None:
    """Optional helper for other parts of the app to update context usage."""
    global _context_used_tokens
    _context_used_tokens = max(0, int(used_tokens))


def set_active_agent_runs_stub(count: int) -> None:
    """Optional helper for other parts of the app to update active agent runs."""
    global _active_agent_runs_stub
    _active_agent_runs_stub = max(0, int(count))


# ---------------------------------------------------------------------------
# GPU Metrics (ROCm)
# ---------------------------------------------------------------------------


def _parse_rocm_smi_output(output: str) -> Optional[GpuMetrics]:
    """
    Very conservative parser for `rocm-smi` output.

    We look for the first GPU entry and attempt to extract:
      - total and used VRAM in MiB
      - GPU utilization percentage

    If parsing fails, return a GpuMetrics with mostly-None fields rather than raising.
    """
    if not output:
        return None

    lines = output.splitlines()
    # Heuristic: find a line containing "GPU" and "MB" or "%".
    gpu_line = None
    for line in lines:
        if "GPU" in line and ("MB" in line or "%" in line):
            gpu_line = line
            break

    name = None
    total_vram_gb: Optional[float] = None
    used_vram_gb: Optional[float] = None
    utilization_pct: Optional[float] = None

    if gpu_line:
        # Extract percentages.
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", gpu_line)
        if pct_match:
            utilization_pct = float(pct_match.group(1))

        # Extract numbers followed by MB (VRAM usage).
        mb_matches = re.findall(r"(\d+(?:\.\d+)?)\s*MB", gpu_line)
        if len(mb_matches) >= 2:
            used_mb = float(mb_matches[0])
            total_mb = float(mb_matches[1])
            used_vram_gb = used_mb / 1024.0
            total_vram_gb = total_mb / 1024.0

    # Try to find a more descriptive name line if present.
    model_line = None
    for line in lines:
        if "card series" in line.lower() or "model" in line.lower():
            model_line = line
            break
    if model_line:
        # Best-effort extraction of model name after a colon.
        parts = model_line.split(":", 1)
        if len(parts) == 2:
            name = parts[1].strip()

    if name is None and total_vram_gb is None and used_vram_gb is None and utilization_pct is None:
        return None

    return GpuMetrics(
        name=name,
        total_vram_gb=total_vram_gb,
        used_vram_gb=used_vram_gb,
        utilization_pct=utilization_pct,
    )


def get_gpu_metrics() -> Optional[GpuMetrics]:
    """
    Attempt to read GPU metrics via ROCm CLI tools.

    Strategy:
      - Try `rocm-smi` first; parse its output.
      - If not available or parsing fails, return None (no GPU info).

    This function must *never* raise on failure; callers depend on graceful degradation.
    """
    # If ROCm isn't installed or hardware is unavailable, this may fail in a variety of ways.
    try:
        proc = subprocess.run(
            ["rocm-smi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.SubprocessError):
        return None

    metrics = _parse_rocm_smi_output(proc.stdout)
    return metrics


# ---------------------------------------------------------------------------
# CPU / Memory Metrics
# ---------------------------------------------------------------------------


def _get_cpu_stats_psutil() -> CpuMetrics:
    assert psutil is not None  # for type checkers
    num_cores = psutil.cpu_count(logical=True) or 1
    # Use a short interval to get a near-real-time sample without blocking too long.
    load_pct = float(psutil.cpu_percent(interval=0.1))
    return CpuMetrics(num_cores=num_cores, load_pct=load_pct)


def _get_cpu_stats_stdlib() -> CpuMetrics:
    num_cores = os.cpu_count() or 1
    load_pct = 0.0
    # Approximate using OS load average if available.
    try:
        one_min, _, _ = os.getloadavg()
        # Convert load average to percentage relative to number of cores.
        load_pct = float(min(max(one_min / num_cores * 100.0, 0.0), 100.0))
    except (OSError, AttributeError):
        load_pct = 0.0
    return CpuMetrics(num_cores=num_cores, load_pct=load_pct)


def get_cpu_metrics() -> CpuMetrics:
    """
    Return CPU metrics using psutil if available, falling back to stdlib.

    This function must not raise.
    """
    try:
        if psutil is not None:
            return _get_cpu_stats_psutil()
        return _get_cpu_stats_stdlib()
    except Exception:  # pragma: no cover - defensive
        return _get_cpu_stats_stdlib()


def _get_memory_stats_psutil() -> MemoryMetrics:
    assert psutil is not None  # for type checkers
    vmem = psutil.virtual_memory()
    total_gb = float(vmem.total) / (1024.0**3)
    used_gb = float(vmem.total - vmem.available) / (1024.0**3)
    return MemoryMetrics(total_gb=total_gb, used_gb=used_gb)


def _get_memory_stats_proc() -> MemoryMetrics:
    """
    Linux /proc/meminfo fallback if psutil is unavailable.

    This is a coarse approximation, but sufficient for status classification.
    """
    mem_total_kb = None
    mem_available_kb = None
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_kb = float(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available_kb = float(line.split()[1])
                if mem_total_kb is not None and mem_available_kb is not None:
                    break
    except OSError:
        # Fallback to dummy values.
        return MemoryMetrics(total_gb=1.0, used_gb=0.0)

    if mem_total_kb is None or mem_available_kb is None:
        return MemoryMetrics(total_gb=1.0, used_gb=0.0)

    total_gb = mem_total_kb / (1024.0**2)
    used_gb = (mem_total_kb - mem_available_kb) / (1024.0**2)
    return MemoryMetrics(total_gb=total_gb, used_gb=used_gb)


def get_memory_metrics() -> MemoryMetrics:
    """
    Return Memory metrics using psutil if available, falling back to /proc.

    This function must not raise.
    """
    try:
        if psutil is not None:
            return _get_memory_stats_psutil()
        return _get_memory_stats_proc()
    except Exception:  # pragma: no cover - defensive
        return _get_memory_stats_proc()


# ---------------------------------------------------------------------------
# Context & Agent Run Metrics
# ---------------------------------------------------------------------------


def get_context_metrics() -> ContextMetrics:
    """
    Stubbed context metrics.

    - total_tokens: from app.config.settings.context_total_tokens if available,
      otherwise a sane default.
    - used_tokens: from the module-level stub `_context_used_tokens`.
    """
    total_tokens = _get_configured_context_total_tokens()
    used_tokens = min(_context_used_tokens, total_tokens)
    return ContextMetrics(total_tokens=total_tokens, used_tokens=used_tokens)


def _get_active_agent_runs() -> int:
    """
    Stubbed active agent run count.

    In a real implementation, this would query an agent manager service or DB.
    """
    return _active_agent_runs_stub


# ---------------------------------------------------------------------------
# Status Aggregation / Classification
# ---------------------------------------------------------------------------


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _max_status(current: SystemStatusLiteral, candidate: SystemStatusLiteral) -> SystemStatusLiteral:
    order = {"nominal": 0, "warning": 1, "critical": 2}
    return candidate if order[candidate] > order[current] else current


def get_system_status() -> SystemStatus:
    """
    Aggregate all metric sources and classify overall system status.

    Heuristics (subject to tuning):
      - CPU:
          warning: load_pct >= 75
          critical: load_pct >= 90
      - Memory:
          warning: used/total >= 0.75
          critical: used/total >= 0.90
      - GPU (if present and metrics available):
          warning: utilization >= 75 OR vram_used/total >= 0.75
          critical: utilization >= 90 OR vram_used/total >= 0.90
      - Context:
          warning: used/total >= 0.80
          critical: used/total >= 0.95
    """
    gpu = get_gpu_metrics()
    cpu = get_cpu_metrics()
    memory = get_memory_metrics()
    context = get_context_metrics()
    active_agent_runs = _get_active_agent_runs()

    warming_up = not model_warmup_service.is_ready()
    warming_reason = model_warmup_service.status_reason() if warming_up else None

    status: SystemStatusLiteral = "nominal"
    reasons: list[str] = []

    # CPU
    if cpu.load_pct >= 90.0:
        status = _max_status(status, "critical")
        reasons.append(f"CPU load very high ({cpu.load_pct:.1f}%).")
    elif cpu.load_pct >= 75.0:
        status = _max_status(status, "warning")
        reasons.append(f"CPU load elevated ({cpu.load_pct:.1f}%).")

    # Memory
    mem_ratio = _ratio(memory.used_gb, memory.total_gb)
    if mem_ratio >= 0.90:
        status = _max_status(status, "critical")
        reasons.append(f"Memory usage very high ({mem_ratio * 100:.1f}%).")
    elif mem_ratio >= 0.75:
        status = _max_status(status, "warning")
        reasons.append(f"Memory usage elevated ({mem_ratio * 100:.1f}%).")

    # GPU (if we have enough info to say anything)
    if gpu is not None:
        gpu_util = gpu.utilization_pct
        vram_ratio: Optional[float] = None
        if gpu.total_vram_gb and gpu.total_vram_gb > 0 and gpu.used_vram_gb is not None:
            vram_ratio = _ratio(gpu.used_vram_gb, gpu.total_vram_gb)

        gpu_critical = False
        gpu_warning = False

        if gpu_util is not None:
            if gpu_util >= 90.0:
                gpu_critical = True
            elif gpu_util >= 75.0:
                gpu_warning = True

        if vram_ratio is not None:
            if vram_ratio >= 0.90:
                gpu_critical = True
            elif vram_ratio >= 0.75:
                gpu_warning = True

        if gpu_critical:
            status = _max_status(status, "critical")
            reasons.append("GPU heavily utilized.")
        elif gpu_warning:
            status = _max_status(status, "warning")
            reasons.append("GPU utilization elevated.")

    # Context
    ctx_ratio = _ratio(context.used_tokens, context.total_tokens)
    if ctx_ratio >= 0.95:
        status = _max_status(status, "critical")
        reasons.append(f"Context budget nearly exhausted ({ctx_ratio * 100:.1f}%).")
    elif ctx_ratio >= 0.80:
        status = _max_status(status, "warning")
        reasons.append(f"Context budget high ({ctx_ratio * 100:.1f}%).")

    reason_str = "; ".join(reasons) if reasons else None
    if warming_reason:
        if reason_str:
            reason_str = f"{reason_str}; {warming_reason}"
        else:
            reason_str = warming_reason

    return SystemStatus(
        status=status,
        reason=reason_str,
        gpu=gpu,
        cpu=cpu,
        memory=memory,
        context=context,
        active_agent_runs=active_agent_runs,
    )

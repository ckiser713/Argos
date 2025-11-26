from __future__ import annotations

from app.db import db_session
from app.domain.models import MessageResponse  # Keep MessageResponse if still needed
from app.domain.system_metrics import SystemStatus
from app.services.system_metrics_service import get_system_status
from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=MessageResponse, summary="Basic liveness probe")
def health_check() -> MessageResponse:
    return MessageResponse(message="ok")


@router.get("/ready", response_model=MessageResponse, summary="Readiness probe with DB check")
def readiness_check() -> MessageResponse:
    """
    Verify critical dependencies (currently SQLite) are reachable.
    """
    with db_session() as conn:
        conn.execute("SELECT 1")
    return MessageResponse(message="ready")


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Get current system status snapshot.",
    description=(
        "Returns a consolidated view of GPU, CPU, memory, context token usage, "
        "and active agent runs for the Cortex Command Center."
    ),
)
async def read_system_status() -> SystemStatus:
    """
    Return the current SystemStatus.

    This endpoint is polled periodically by the frontend header and Command Center.
    """
    # Synchronous metrics are quick enough; no need for async offload.
    # Guardrail: require Nix env for local runs (IN_NIX_SHELL set) when not in production.
    return get_system_status()

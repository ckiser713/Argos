from __future__ import annotations

from app.db import db_session
from app.domain.models import MessageResponse  # Keep MessageResponse if still needed
from app.domain.system_metrics import SystemStatus
from app.services.system_metrics_service import get_system_status
from app.config import get_settings
from fastapi import APIRouter
import requests
from typing import Dict, Any
import os

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


@router.get('/models/lanes', summary='Get configured model lanes and their settings')
def get_model_lanes():
    settings = get_settings()
    lanes = {
        'orchestrator': {
            'url': settings.lane_orchestrator_url,
            'model': settings.lane_orchestrator_model,
            'backend': settings.lane_orchestrator_backend,
            'model_path': getattr(settings, 'lane_orchestrator_model_path', ''),
        },
        'coder': {
            'url': settings.lane_coder_url,
            'model': settings.lane_coder_model,
            'backend': settings.lane_coder_backend,
            'model_path': getattr(settings, 'lane_coder_model_path', ''),
        },
        'super_reader': {
            'url': settings.lane_super_reader_url,
            'model': settings.lane_super_reader_model,
            'backend': settings.lane_super_reader_backend,
            'model_path': getattr(settings, 'lane_super_reader_model_path', ''),
        },
        'fast_rag': {
            'url': settings.lane_fast_rag_url,
            'model': settings.lane_fast_rag_model,
            'backend': settings.lane_fast_rag_backend,
            'model_path': getattr(settings, 'lane_fast_rag_model_path', ''),
        },
        'governance': {
            'url': settings.lane_governance_url,
            'model': settings.lane_governance_model,
            'backend': settings.lane_governance_backend,
            'model_path': getattr(settings, 'lane_governance_model_path', ''),
        },
    }
    return {'lanes': lanes}


@router.get('/models/status', summary='Get basic availability status of configured lane endpoints')
def get_model_status():
    lanes_info = get_model_lanes().get('lanes', {})
    status: Dict[str, bool] = {}
    # Support a test-only override to mark lanes available without real models.
    # When `CORTEX_E2E_MOCK_LANES` is set to a truthy value, return True for all lanes.
    mock_lanes = os.environ.get('CORTEX_E2E_MOCK_LANES')
    if mock_lanes and mock_lanes != "0":
        for lane in lanes_info.keys():
            status[lane] = True
        return {'status': status}
    for lane, info in lanes_info.items():
        url = info.get('url')
        if url:
            try:
                # simple ping of the root endpoint (not v1)
                ping_url = url.replace('/v1', '/')
                resp = requests.get(ping_url, timeout=1)
                status[lane] = resp.status_code < 500
            except Exception:
                status[lane] = False
        else:
            status[lane] = False
    return {'status': status}

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from app.config import get_settings
from app.domain.models import MessageResponse  # Keep MessageResponse if still needed
from app.domain.system_metrics import SystemStatus
from app.services.health_service import readiness_report
from app.services.qdrant_service import qdrant_service
from app.services.system_metrics_service import get_system_status
from fastapi import APIRouter, HTTPException
import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


class EmbeddingHealthResponse(BaseModel):
    ready: bool
    can_generate_embeddings: bool
    qdrant_connected: bool
    device: Optional[str] = None
    default_model: Optional[str] = None
    code_model: Optional[str] = None
    error: Optional[str] = None
    client_error: Optional[str] = None


@router.get("/health", response_model=MessageResponse, summary="Basic liveness probe")
def health_check() -> MessageResponse:
    return MessageResponse(message="ok")


@router.get("/ready", response_model=MessageResponse, summary="Readiness probe with DB check")
def readiness_check() -> MessageResponse:
    """
    Verify critical dependencies (currently SQLite) are reachable.
    """
    settings = get_settings()
    report = readiness_report(settings)
    qdrant_health = report.get("qdrant", {})

    if not report.get("ready"):
        raise HTTPException(status_code=503, detail=report.get("reason") or "Not ready")

    if not qdrant_health.get("can_generate_embeddings"):
        logger.warning(
            "Embeddings unavailable; serving read-only or text-only results.",
            extra={"event": "embeddings.health.warning"},
        )
    return MessageResponse(message="ready")


@router.get(
    "/embeddings/health",
    response_model=EmbeddingHealthResponse,
    summary="Embedding/Qdrant readiness and device info",
)
def embedding_health() -> EmbeddingHealthResponse:
    status = qdrant_service.get_health()
    return EmbeddingHealthResponse(
        ready=bool(status.get("ready")),
        can_generate_embeddings=bool(status.get("can_generate_embeddings")),
        qdrant_connected=bool(status.get("qdrant_connected")),
        device=status.get("device"),
        default_model=status.get("default_model"),
        code_model=status.get("code_model"),
        error=status.get("embedding_error") or status.get("code_embedding_error"),
        client_error=status.get("client_error"),
    )


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Get current system status snapshot.",
    description=(
        "Returns a consolidated view of GPU, CPU, memory, context token usage, "
        "and active agent runs for the Argos Command Center."
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

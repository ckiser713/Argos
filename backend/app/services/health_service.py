from __future__ import annotations

import logging
import time
from typing import Any, Dict

import requests

from app.config import Settings, get_settings
from app.database import check_database_connection
from app.services.model_warmup_service import build_lane_health_endpoints
from app.services.qdrant_service import qdrant_service

logger = logging.getLogger(__name__)


def _probe_endpoint(url: str, timeout: float = 1.5) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        resp = requests.get(url, timeout=timeout)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "endpoint": url,
            "ok": 200 <= resp.status_code < 400,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
        }
    except requests.RequestException as exc:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "endpoint": url,
            "ok": False,
            "error": str(exc),
            "latency_ms": latency_ms,
        }


def probe_model_services(settings: Settings) -> Dict[str, Any]:
    """
    Probe configured model lane health endpoints for reachability.
    """
    endpoints = build_lane_health_endpoints(settings)
    if not endpoints:
        return {"all_ok": True, "endpoints": []}

    results = [_probe_endpoint(url) for url in endpoints]
    all_ok = all(result.get("ok") for result in results)
    return {"all_ok": all_ok, "endpoints": results}


def readiness_report(settings: Settings | None = None) -> Dict[str, Any]:
    """
    Run readiness checks for critical dependencies.

    Returns a structured payload describing the state of DB, Qdrant, embeddings,
    and model lane services.
    """
    settings = settings or get_settings()

    db_ok = check_database_connection()

    qdrant_health: Dict[str, Any] = {}
    qdrant_ok = False
    embeddings_ok = not settings.require_embeddings

    try:
        qdrant_health = qdrant_service.ensure_ready(require_embeddings=settings.require_embeddings)
        qdrant_ok = bool(qdrant_health.get("qdrant_connected"))
        embeddings_ok = bool(qdrant_health.get("can_generate_embeddings")) or embeddings_ok
    except Exception as exc:  # noqa: BLE001
        logger.error("Qdrant/embedding readiness failed: %s", exc)
        qdrant_health = {"client_error": str(exc), "ready": False}

    model_probe = probe_model_services(settings)

    ready = bool(db_ok and qdrant_ok and embeddings_ok and model_probe.get("all_ok"))
    reasons = []
    if not db_ok:
        reasons.append("database")
    if not qdrant_ok:
        reasons.append("qdrant")
    if not embeddings_ok:
        reasons.append("embeddings")
    if not model_probe.get("all_ok"):
        reasons.append("model_services")

    return {
        "ready": ready,
        "database": {"connected": db_ok},
        "qdrant": qdrant_health,
        "model_services": model_probe,
        "reason": ", ".join(reasons) if reasons else None,
    }


def liveness() -> Dict[str, str]:
    return {"status": "ok"}



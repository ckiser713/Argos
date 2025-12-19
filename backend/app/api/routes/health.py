from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.health_service import liveness, readiness_report

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
def healthz():
    return liveness()


@router.get("/readyz", summary="Readiness probe")
def readyz():
    report = readiness_report()
    if not report.get("ready"):
        raise HTTPException(status_code=503, detail=report.get("reason") or "not ready")
    return report




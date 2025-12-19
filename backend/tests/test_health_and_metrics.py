from __future__ import annotations

from fastapi.testclient import TestClient

from app.services import health_service
from app.services import qdrant_service


def test_healthz_ok(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"


def test_readyz_success(monkeypatch, client: TestClient) -> None:
    monkeypatch.setattr(health_service, "check_database_connection", lambda: True)
    monkeypatch.setattr(
        qdrant_service.qdrant_service,
        "ensure_ready",
        lambda require_embeddings=False: {
            "ready": True,
            "qdrant_connected": True,
            "can_generate_embeddings": True,
        },
    )
    monkeypatch.setattr(
        health_service,
        "probe_model_services",
        lambda settings: {"all_ok": True, "endpoints": []},
    )

    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ready") is True
    assert body.get("qdrant", {}).get("qdrant_connected") is True


def test_metrics_endpoint_exposes_core_metrics(client: TestClient) -> None:
    # Trigger at least one request for counters
    client.get("/healthz")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    payload = resp.text
    assert "cortex_http_requests_total" in payload
    assert "cortex_http_request_duration_seconds" in payload



# tests/conftest.py
import os
import sys
import tempfile
from pathlib import Path

import pytest
import uuid
from app.config import get_settings
from fastapi.testclient import TestClient




@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped TestClient for the FastAPI app."""
    os.environ.setdefault("CORTEX_TASKS_EAGER", "true")
    os.environ.setdefault("CORTEX_STORAGE_BACKEND", "local")
    os.environ.setdefault(
        "CORTEX_STORAGE_LOCAL_DIR",
        str(Path(tempfile.gettempdir()) / "cortex_ingest_test_uploads"),
    )
    get_settings.cache_clear()
    settings = get_settings()
    db_path = Path(settings.atlas_db_path)
    if db_path.exists():
        db_path.unlink()
    from app.db import init_db
    init_db()

    from app.main import app

    return TestClient(app)


@pytest.fixture
def project(client: TestClient) -> dict:
    """
    Create a fresh project for tests that need a project-scoped resource.

    The backend supports POST /api/projects with a `name`
    (and optionally `description`) field and returns a Project-like JSON object
    with an `id`.
    """
    unique_name = f"Test Project {uuid.uuid4()}"
    payload = {
        "name": unique_name,
        "description": "Project created for backend tests.",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    return data

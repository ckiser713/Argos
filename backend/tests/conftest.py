# tests/conftest.py
import sys
from pathlib import Path

import pytest
from app.config import get_settings
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped TestClient for the FastAPI app."""
    settings = get_settings()
    db_path = Path(settings.atlas_db_path)
    if db_path.exists():
        db_path.unlink()

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
    payload = {
        "name": "Test Project",
        "description": "Project created for backend tests.",
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data
    assert data["name"] == payload["name"]
    return data

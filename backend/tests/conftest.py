# tests/conftest.py
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


# Ensure the backend package is importable when tests are executed from the
# repository root. This keeps the FastAPI app import stable without relying on
# external installation steps.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.main import app  # assumes your FastAPI instance is named `app` here


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def project(client: TestClient) -> dict:
    """
    Create a fresh project for tests that need a project-scoped resource.

    The backend is expected to support POST /api/projects with at least a `name`
    (and optionally `description`) field and return a Project-like JSON object
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

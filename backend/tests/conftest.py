# tests/conftest.py
import pytest
from fastapi.testclient import TestClient

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

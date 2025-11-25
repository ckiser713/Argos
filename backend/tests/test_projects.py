# tests/test_projects.py
from fastapi.testclient import TestClient


def test_list_projects_initial(client: TestClient) -> None:
    """
    GET /api/projects returns a paginated list of projects.
    """
    response = client.get("/api/projects")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert "items" in data

    for project in data["items"]:
        assert isinstance(project, dict)
        assert "id" in project
        assert "name" in project


def test_create_project_and_list_again(client: TestClient) -> None:
    """
    POST /api/projects should create a project and then be visible via GET.
    """
    payload = {
        "name": "Cortex Backend Test Project",
        "description": "Used in FastAPI tests.",
    }
    create_resp = client.post("/api/projects", json=payload)

    assert create_resp.status_code in (200, 201)
    created = create_resp.json()
    assert isinstance(created, dict)
    assert "id" in created
    assert created["name"] == payload["name"]

    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200

    projects = list_resp.json()["items"]
    ids = {p["id"] for p in projects if "id" in p}
    assert created["id"] in ids

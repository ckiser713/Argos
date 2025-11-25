# tests/test_projects.py
from fastapi.testclient import TestClient


def test_list_projects_initial(client: TestClient) -> None:
    """
    GET /api/projects should return a JSON list of projects.

    The list may be empty or pre-populated with dummy data, but each project
    must at least have `id` and `name`.
    """
    response = client.get("/api/projects")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    for project in data:
        assert isinstance(project, dict)
        assert "id" in project
        assert "name" in project
        # Optional but good sanity checks if your domain includes them:
        # if "created_at" in project:
        #     assert isinstance(project["created_at"], str)


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

    # Verify it appears in the project list
    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200

    projects = list_resp.json()
    assert isinstance(projects, list)
    ids = {p["id"] for p in projects if "id" in p}
    assert created["id"] in ids

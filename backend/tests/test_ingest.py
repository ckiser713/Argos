# tests/test_ingest.py
from fastapi.testclient import TestClient


def test_list_ingest_jobs_for_project_initial(client: TestClient, project: dict) -> None:
    """
    GET /api/projects/{projectId}/ingest/jobs should return a paginated list of ingest jobs
    for that project (possibly empty).
    """
    project_id = project["id"]
    resp = client.get(f"/api/projects/{project_id}/ingest/jobs")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)

    for job in data["items"]:
        assert isinstance(job, dict)
        assert "id" in job
        assert job.get("project_id") == project_id
        assert job.get("status") in {"queued", "running", "completed", "failed", "cancelled"}
        if "stage" in job:
            assert isinstance(job["stage"], str)


def test_create_ingest_job_for_project(client: TestClient, project: dict) -> None:
    """
    POST /api/projects/{projectId}/ingest/jobs should create a new ingest job
    associated with the project and return its representation.
    """
    project_id = project["id"]

    payload = {
        "source_path": "file://backend-tests-notes.md",
    }

    create_resp = client.post(f"/api/projects/{project_id}/ingest/jobs", json=payload)
    assert create_resp.status_code in (200, 201)

    created = create_resp.json()
    assert isinstance(created, dict)
    assert "id" in created
    assert created.get("project_id") == project_id
    assert created.get("source_path") == payload["source_path"]

    if "status" in created:
        assert created["status"] in {"queued", "running", "completed", "failed", "cancelled"}
    if "stage" in created:
        assert isinstance(created["stage"], str)

    list_resp = client.get(f"/api/projects/{project_id}/ingest/jobs")
    assert list_resp.status_code == 200
    jobs_data = list_resp.json()
    jobs = jobs_data["items"]
    assert any(job["id"] == created["id"] for job in jobs)

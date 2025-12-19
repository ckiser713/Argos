# tests/test_ingest.py
from time import sleep

from fastapi.testclient import TestClient

from app.services.ingest_service import ingest_service


def test_list_ingest_jobs_for_project_initial(client: TestClient, project: dict) -> None:
    """Listing ingest jobs should return a paginated payload (possibly empty)."""
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
    """Creating a job returns metadata and enqueues processing."""
    project_id = project["id"]
    payload = {"source_uri": "file://backend-tests-notes.md"}

    create_resp = client.post(f"/api/projects/{project_id}/ingest/jobs", json=payload)
    assert create_resp.status_code in (200, 201)

    created = create_resp.json()
    assert isinstance(created, dict)
    assert "id" in created
    assert created.get("project_id") == project_id
    assert created.get("source_uri") == payload["source_uri"]

    list_resp = client.get(f"/api/projects/{project_id}/ingest/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()["items"]
    assert any(job["id"] == created["id"] for job in jobs)


def test_upload_creates_job_and_persists_metadata(client: TestClient, project: dict) -> None:
    """Upload endpoint should store the file durably and return checksum/size info."""
    project_id = project["id"]
    file_bytes = b"hello durable ingest"

    upload_resp = client.post(
        f"/api/projects/{project_id}/ingest/upload",
        files={"file": ("hello.txt", file_bytes, "text/plain")},
    )
    assert upload_resp.status_code == 200
    payload = upload_resp.json()
    job_id = payload["job_id"]

    for _ in range(10):
        job_resp = client.get(f"/api/projects/{project_id}/ingest/jobs/{job_id}")
        assert job_resp.status_code == 200
        job = job_resp.json()
        if job["status"] == "completed":
            break
        sleep(0.1)

    assert job["status"] == "completed"
    assert job["byte_size"] == len(file_bytes)
    assert job["checksum"]
    assert job["source_uri"].startswith("file:")


def test_ingest_retry_behavior(monkeypatch, client: TestClient, project: dict) -> None:
    """Transient failures should be retried and eventually succeed in eager mode."""
    project_id = project["id"]
    attempts = {"count": 0}
    original_process = ingest_service.process_job

    async def flaky_process(job_id: str, mark_failed: bool = True):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient failure")
        return await original_process(job_id, mark_failed=mark_failed)

    monkeypatch.setattr(ingest_service, "process_job", flaky_process)

    create_resp = client.post(
        f"/api/projects/{project_id}/ingest",
        json={"source_type": "text", "content": "retryable ingest"},
    )
    assert create_resp.status_code in (200, 201)
    job_id = create_resp.json()["job_id"]

    final_status = None
    for _ in range(15):
        job_resp = client.get(f"/api/projects/{project_id}/ingest/jobs/{job_id}")
        assert job_resp.status_code == 200
        final_status = job_resp.json()["status"]
        if final_status in {"completed", "failed"}:
            break
        sleep(0.1)

    assert attempts["count"] >= 2
    assert final_status == "completed"

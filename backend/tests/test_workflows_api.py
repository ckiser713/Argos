# tests/test_workflows_api.py
"""
Test specification: Workflows API
Tests for workflow execution endpoints including execute, cancel, pause, resume operations.
"""
from fastapi.testclient import TestClient


def test_list_workflow_graphs(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/workflows/graphs"""
    project_id = project["id"]
    resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_create_workflow_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/workflows/runs"""
    project_id = project["id"]
    # First need a workflow graph
    graphs_resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    if graphs_resp.status_code == 200 and graphs_resp.json():
        workflow_id = graphs_resp.json()[0]["id"]
        payload = {
            "workflow_id": workflow_id,
            "input_data": {"query": "test"},
        }
        resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data


def test_get_workflow_run(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/workflows/runs/{runId}"""
    project_id = project["id"]
    graphs_resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    if graphs_resp.status_code == 200 and graphs_resp.json():
        workflow_id = graphs_resp.json()[0]["id"]
        payload = {"workflow_id": workflow_id, "input_data": {}}
        create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
        if create_resp.status_code in (200, 201):
            run_id = create_resp.json()["id"]
            resp = client.get(f"/api/projects/{project_id}/workflows/runs/{run_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert "id" in data


def test_execute_workflow_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/workflows/runs/{runId}/execute"""
    project_id = project["id"]
    graphs_resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    if graphs_resp.status_code == 200 and graphs_resp.json():
        workflow_id = graphs_resp.json()[0]["id"]
        payload = {"workflow_id": workflow_id, "input_data": {}}
        create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
        if create_resp.status_code in (200, 201):
            run_id = create_resp.json()["id"]
            resp = client.post(f"/api/projects/{project_id}/workflows/runs/{run_id}/execute")
            assert resp.status_code in (200, 202)


def test_cancel_workflow_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/workflows/runs/{runId}/cancel"""
    project_id = project["id"]
    graphs_resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    if graphs_resp.status_code == 200 and graphs_resp.json():
        workflow_id = graphs_resp.json()[0]["id"]
        payload = {"workflow_id": workflow_id, "input_data": {}}
        create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
        if create_resp.status_code in (200, 201):
            run_id = create_resp.json()["id"]
            resp = client.post(f"/api/projects/{project_id}/workflows/runs/{run_id}/cancel")
            assert resp.status_code in (200, 400)


def test_get_workflow_run_status(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/workflows/runs/{runId}/status"""
    project_id = project["id"]
    graphs_resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    if graphs_resp.status_code == 200 and graphs_resp.json():
        workflow_id = graphs_resp.json()[0]["id"]
        payload = {"workflow_id": workflow_id, "input_data": {}}
        create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
        if create_resp.status_code in (200, 201):
            run_id = create_resp.json()["id"]
            resp = client.get(f"/api/projects/{project_id}/workflows/runs/{run_id}/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data


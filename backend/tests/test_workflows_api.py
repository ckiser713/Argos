# tests/test_workflows_api.py
"""
Test specification: Workflows API
Tests for workflow execution endpoints including execute, cancel, pause, resume operations.
"""
from fastapi.testclient import TestClient


def _create_graph(client: TestClient, project_id: str) -> str:
    payload = {
        "name": "Sample Workflow",
        "description": "Graph created for tests",
        "nodes": [
            {"id": "n1", "label": "Start", "x": 0, "y": 0},
            {"id": "n2", "label": "Finish", "x": 200, "y": 0},
        ],
        "edges": [
            {"id": "e-start", "source": "__start__", "target": "n1"},
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e-end", "source": "n2", "target": "__end__"},
        ],
    }
    resp = client.post(f"/api/projects/{project_id}/workflows/graphs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    return data["id"]


def test_list_workflow_graphs(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/workflows/graphs"""
    project_id = project["id"]
    _create_graph(client, project_id)
    resp = client.get(f"/api/projects/{project_id}/workflows/graphs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_create_workflow_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/workflows/runs"""
    project_id = project["id"]
    workflow_id = _create_graph(client, project_id)
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
    workflow_id = _create_graph(client, project_id)
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
    workflow_id = _create_graph(client, project_id)
    payload = {"workflow_id": workflow_id, "input_data": {}}
    create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.post(f"/api/projects/{project_id}/workflows/runs/{run_id}/execute")
        assert resp.status_code in (200, 202)


def test_cancel_workflow_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/workflows/runs/{runId}/cancel"""
    project_id = project["id"]
    workflow_id = _create_graph(client, project_id)
    payload = {"workflow_id": workflow_id, "input_data": {}}
    create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.post(f"/api/projects/{project_id}/workflows/runs/{run_id}/cancel")
        assert resp.status_code in (200, 400)


def test_get_workflow_run_status(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/workflows/runs/{runId}/status"""
    project_id = project["id"]
    workflow_id = _create_graph(client, project_id)
    payload = {"workflow_id": workflow_id, "input_data": {}}
    create_resp = client.post(f"/api/projects/{project_id}/workflows/runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/workflows/runs/{run_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

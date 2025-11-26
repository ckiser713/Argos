# tests/test_agents_api.py
"""
Test specification: Agents API
Comprehensive tests for agent endpoints including run details, steps, messages, cancel operations.
"""
from fastapi.testclient import TestClient


def test_list_agent_runs(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/agent-runs"""
    project_id = project["id"]
    resp = client.get(f"/api/projects/{project_id}/agent-runs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_agent_run(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/agent-runs/{runId}"""
    project_id = project["id"]
    # First create a run
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["project_id"] == project_id


def test_list_agent_run_steps(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/agent-runs/{runId}/steps"""
    project_id = project["id"]
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}/steps")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


def test_list_agent_run_messages(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/agent-runs/{runId}/messages"""
    project_id = project["id"]
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


def test_list_agent_run_node_states(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/agent-runs/{runId}/node-states"""
    project_id = project["id"]
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}/node-states")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


def test_append_agent_run_message(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/agent-runs/{runId}/messages"""
    project_id = project["id"]
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        message_payload = {
            "content": "Follow-up question",
            "context_item_ids": [],
        }
        resp = client.post(f"/api/projects/{project_id}/agent-runs/{run_id}/messages", json=message_payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data
        assert data["content"] == message_payload["content"]


def test_cancel_agent_run(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/agent-runs/{runId}/cancel"""
    project_id = project["id"]
    payload = {
        "project_id": project_id,
        "agent_id": "project_manager",
        "input_prompt": "Test query",
    }
    create_resp = client.post(f"/api/projects/{project_id}/agent-runs", json=payload)
    if create_resp.status_code in (200, 201):
        run_id = create_resp.json()["id"]
        resp = client.post(f"/api/projects/{project_id}/agent-runs/{run_id}/cancel")
        # Should succeed or return 400 if already completed
        assert resp.status_code in (200, 400)

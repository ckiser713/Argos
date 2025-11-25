# tests/test_context_api.py
"""
Test specification: Context API
Tests for context management endpoints including budget calculations and item operations.
"""
from fastapi.testclient import TestClient


def test_get_context_budget(client: TestClient, project: dict) -> None:
    """Test GET /api/projects/{projectId}/context"""
    project_id = project["id"]
    resp = client.get(f"/api/projects/{project_id}/context")
    assert resp.status_code == 200
    data = resp.json()
    assert "totalTokens" in data
    assert "usedTokens" in data
    assert "availableTokens" in data
    assert "items" in data


def test_add_context_items(client: TestClient, project: dict) -> None:
    """Test POST /api/projects/{projectId}/context/items"""
    project_id = project["id"]
    payload = {
        "items": [
            {
                "name": "test_document.pdf",
                "type": "PDF",
                "tokens": 1000,
            }
        ]
    }
    resp = client.post(f"/api/projects/{project_id}/context/items", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "budget" in data


def test_update_context_item(client: TestClient, project: dict) -> None:
    """Test PATCH /api/projects/{projectId}/context/items/{contextItemId}"""
    project_id = project["id"]
    # First add an item
    add_payload = {
        "items": [
            {
                "name": "test_document.pdf",
                "type": "PDF",
                "tokens": 1000,
            }
        ]
    }
    add_resp = client.post(f"/api/projects/{project_id}/context/items", json=add_payload)
    if add_resp.status_code == 200:
        item_id = add_resp.json()["items"][0]["id"]
        update_payload = {"pinned": True}
        resp = client.patch(f"/api/projects/{project_id}/context/items/{item_id}", json=update_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data


def test_remove_context_item(client: TestClient, project: dict) -> None:
    """Test DELETE /api/projects/{projectId}/context/items/{contextItemId}"""
    project_id = project["id"]
    # First add an item
    add_payload = {
        "items": [
            {
                "name": "test_document.pdf",
                "type": "PDF",
                "tokens": 1000,
            }
        ]
    }
    add_resp = client.post(f"/api/projects/{project_id}/context/items", json=add_payload)
    if add_resp.status_code == 200:
        item_id = add_resp.json()["items"][0]["id"]
        resp = client.delete(f"/api/projects/{project_id}/context/items/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "budget" in data


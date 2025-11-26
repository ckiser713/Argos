import pytest
from app.main import create_app
from app.repos import mode_repo
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client_mode() -> TestClient:
    app = create_app()
    # Router is already included in create_app() with /api prefix
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_mode_repo():
    # Clear the in-memory store before each test to ensure isolation
    mode_repo._PROJECT_SETTINGS_STORE = {}
    yield


def test_get_default_project_mode(client_mode: TestClient) -> None:
    project_id = "test-project-default"
    resp = client_mode.get(f"/api/projects/{project_id}/mode")
    assert resp.status_code == 200

    data = resp.json()
    assert data["project_id"] == project_id
    assert data["mode"] == "normal"
    assert data["llm_temperature"] == 0.2
    assert data["validation_passes"] == 1
    assert data["max_parallel_tools"] == 8


def test_patch_mode_updates_mode_and_overrides(client_mode: TestClient) -> None:
    project_id = "test-project-patch"

    resp = client_mode.patch(
        f"/api/projects/{project_id}/mode",
        json={
            "mode": "paranoid",
            "llm_temperature": 0.1,
            "validation_passes": 4,
            "max_parallel_tools": 2,
        },
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["project_id"] == project_id
    assert data["mode"] == "paranoid"
    assert data["llm_temperature"] == 0.1
    assert data["validation_passes"] == 4
    assert data["max_parallel_tools"] == 2

    # Subsequent GET should reflect the updated settings.
    resp2 = client_mode.get(f"/api/projects/{project_id}/mode")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2 == data


def test_patch_mode_requires_at_least_one_field(client_mode: TestClient) -> None:
    project_id = "test-project-bad-patch"

    resp = client_mode.patch(f"/api/projects/{project_id}/mode", json={})
    assert resp.status_code == 400
    assert "At least one field" in resp.json()["detail"]


def test_patch_mode_partial_update(client_mode: TestClient) -> None:
    project_id = "test-project-partial"

    # Set some initial non-default settings
    client_mode.patch(
        f"/api/projects/{project_id}/mode",
        json={
            "mode": "paranoid",
            "llm_temperature": 0.15,
        },
    )

    # Patch only validation_passes
    resp = client_mode.patch(
        f"/api/projects/{project_id}/mode",
        json={"validation_passes": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["mode"] == "paranoid"  # Should retain previous mode
    assert data["llm_temperature"] == 0.15  # Should retain previous temperature
    assert data["validation_passes"] == 5  # Should update this field
    assert data["max_parallel_tools"] == 8  # Should retain default if not set initially

    # Verify with GET
    get_resp = client_mode.get(f"/api/projects/{project_id}/mode")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data == data

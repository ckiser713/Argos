from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from jose import jwt


def _build_client(monkeypatch, tmp_path, *, secret: str, access_minutes: int = 15) -> TestClient:
    db_path = tmp_path / f"auth_{uuid.uuid4().hex}.db"
    monkeypatch.setenv("CORTEX_ENV", "local")
    monkeypatch.setenv("CORTEX_SKIP_AUTH", "false")
    monkeypatch.setenv("CORTEX_AUTH_SECRET", secret)
    monkeypatch.setenv("CORTEX_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CORTEX_ACCESS_TOKEN_MINUTES", str(access_minutes))
    monkeypatch.setenv("CORTEX_REFRESH_TOKEN_DAYS", "7")

    from app.config import get_settings
    from app.db import init_db
    from app.main import create_app

    get_settings.cache_clear()
    init_db()
    app = create_app()
    return TestClient(app)


def test_default_credentials_absent(monkeypatch, tmp_path) -> None:
    secret = "test-secret-" + "a" * 32
    client = _build_client(monkeypatch, tmp_path, secret=secret)

    for username, password in [("admin", "admin"), ("cortex", "cortex")]:
        resp = client.post("/api/auth/token", data={"username": username, "password": password})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_creation_and_login(monkeypatch, tmp_path) -> None:
    secret = "test-secret-" + "b" * 32
    client = _build_client(monkeypatch, tmp_path, secret=secret)

    bootstrap = client.post(
        "/api/auth/bootstrap-admin",
        json={"username": "root", "password": "Str0ngPass!"},
    )
    assert bootstrap.status_code == status.HTTP_200_OK
    admin_payload = bootstrap.json()

    login = client.post(
        "/api/auth/token",
        data={"username": "root", "password": "Str0ngPass!"},
    )
    assert login.status_code == status.HTTP_200_OK
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == status.HTTP_200_OK
    assert me.json()["username"] == "root"

    create_user = client.post(
        "/api/auth/users",
        json={"username": "newuser", "password": "AnotherPass123!", "roles": ["user"]},
        headers=headers,
    )
    assert create_user.status_code == status.HTTP_200_OK
    assert create_user.json()["username"] == "newuser"

    refreshed = client.post("/api/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == status.HTTP_200_OK
    assert refreshed.json()["access_token"]


def test_token_expiry_and_revocation(monkeypatch, tmp_path) -> None:
    secret = "test-secret-" + "c" * 32
    client = _build_client(monkeypatch, tmp_path, secret=secret)

    bootstrap = client.post(
        "/api/auth/bootstrap-admin",
        json={"username": "alice", "password": "Sup3rSecret!"},
    )
    assert bootstrap.status_code == status.HTTP_200_OK
    admin = bootstrap.json()

    login = client.post(
        "/api/auth/token",
        data={"username": "alice", "password": "Sup3rSecret!"},
    )
    assert login.status_code == status.HTTP_200_OK
    tokens = login.json()

    expired_payload = {
        "sub": admin["id"],
        "username": admin["username"],
        "roles": admin.get("roles", []),
        "scopes": [],
        "tv": 1,
        "jti": uuid.uuid4().hex,
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")
    expired_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert expired_me.status_code == status.HTTP_401_UNAUTHORIZED

    auth_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout = client.post("/api/auth/logout", json={"revoke_all": False}, headers=auth_headers)
    assert logout.status_code == status.HTTP_200_OK

    post_logout = client.get("/api/auth/me", headers=auth_headers)
    assert post_logout.status_code == status.HTTP_401_UNAUTHORIZED


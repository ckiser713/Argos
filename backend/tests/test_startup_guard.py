import logging

import pytest

from app.config import get_settings
from app.main import validate_runtime_prereqs


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    """Ensure each test sees fresh settings/env."""
    get_settings.cache_clear()
    for key in [
        "CORTEX_ENV",
        "CORTEX_DATABASE_URL",
        "CORTEX_DB_URL",
        "IN_NIX_SHELL",
        "RUNNING_IN_DOCKER",
        "CORTEX_ALLOW_NON_NIX",
        "CORTEX_AUTH_SECRET",
    ]:
        monkeypatch.delenv(key, raising=False)
    yield
    get_settings.cache_clear()


def test_local_environment_allows_nix(monkeypatch):
    monkeypatch.setenv("CORTEX_ENV", "local")
    monkeypatch.setenv("IN_NIX_SHELL", "1")
    settings = get_settings()

    validate_runtime_prereqs(settings, logging.getLogger("test-local"))


def test_container_prod_allows_without_nix(monkeypatch):
    monkeypatch.setenv("CORTEX_ENV", "production")
    monkeypatch.setenv("CORTEX_DATABASE_URL", "postgresql://user:pass@postgres:5432/db")
    monkeypatch.setenv("CORTEX_AUTH_SECRET", "secret")
    monkeypatch.setenv("RUNNING_IN_DOCKER", "1")

    settings = get_settings()
    validate_runtime_prereqs(settings, logging.getLogger("test-docker"))


def test_missing_database_url_raises(monkeypatch):
    monkeypatch.setenv("CORTEX_ENV", "production")
    monkeypatch.setenv("CORTEX_AUTH_SECRET", "secret")

    with pytest.raises(ValueError):
        get_settings()


def test_non_local_without_nix_or_docker_raises(monkeypatch):
    monkeypatch.setenv("CORTEX_ENV", "strix")
    monkeypatch.setenv("CORTEX_DATABASE_URL", "postgresql://user:pass@postgres:5432/db")
    monkeypatch.setenv("CORTEX_AUTH_SECRET", "secret")

    settings = get_settings()
    with pytest.raises(RuntimeError):
        validate_runtime_prereqs(settings, logging.getLogger("test-guard"))


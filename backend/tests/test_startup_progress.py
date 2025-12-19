import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import get_settings
from app.services.vllm_lane_manager import warmup_lanes_at_startup
from app.services.model_warmup_service import model_warmup_service


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Ensure each test sees fresh settings/env."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestStartupProgressEndpoint:
    """Test the /api/system/startup-progress endpoint."""

    def test_startup_progress_basic_structure(self, client):
        """Test that startup progress endpoint returns expected structure."""
        response = client.get("/api/system/startup-progress")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "database" in data
        assert "embeddings" in data
        assert "lanes" in data
        assert "ready" in data
        assert "timestamp" in data

        # Check embeddings structure
        assert "ready" in data["embeddings"]
        assert "info" in data["embeddings"]

        # Check lanes is a dict
        assert isinstance(data["lanes"], dict)

    def test_startup_progress_caching(self, client):
        """Test that startup progress endpoint caches results."""
        # First request
        response1 = client.get("/api/system/startup-progress")
        data1 = response1.json()

        # Second request (should be cached)
        response2 = client.get("/api/system/startup-progress")
        data2 = response2.json()

        # Should be the same data (cached)
        assert data1["timestamp"] == data2["timestamp"]

    @patch("app.api.routes.system.check_database_connection")
    def test_startup_progress_database_status(self, mock_db_check, client):
        """Test database status reporting."""
        from app.api.routes import system
        
        mock_db_check.return_value = True
        system._startup_progress_cache = {"data": None, "timestamp": 0.0}
        response = client.get("/api/system/startup-progress")
        assert response.json()["database"] is True

        mock_db_check.return_value = False
        system._startup_progress_cache = {"data": None, "timestamp": 0.0}
        response = client.get("/api/system/startup-progress")
        assert response.json()["database"] is False


class TestGracefulLaneWarmup:
    """Test graceful lane warmup with timeout."""

    @pytest.fixture
    def mock_settings_fixture(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.lane_warmup_timeout = 1  # Short timeout for testing
        settings.strict_lane_startup = True
        return settings

    @patch("app.services.vllm_lane_manager.initialize_lane_manager")
    @patch("app.services.vllm_lane_manager.settings")
    @patch("asyncio.wait_for")
    @pytest.mark.asyncio
    async def test_lane_warmup_success(self, mock_wait_for, mock_settings, mock_init_lane, mock_settings_fixture):
        """Test successful lane warmup."""
        mock_settings.lane_warmup_timeout = mock_settings_fixture.lane_warmup_timeout
        mock_settings.strict_lane_startup = mock_settings_fixture.strict_lane_startup
        mock_wait_for.return_value = None  # Success

        await warmup_lanes_at_startup()

        mock_wait_for.assert_called_once()

    @patch("app.services.vllm_lane_manager.initialize_lane_manager")
    @patch("app.services.vllm_lane_manager.settings")
    @patch("asyncio.wait_for")
    @pytest.mark.asyncio
    async def test_lane_warmup_timeout_strict_mode(self, mock_wait_for, mock_settings, mock_init_lane, mock_settings_fixture):
        """Test lane warmup timeout in strict mode raises RuntimeError."""
        mock_settings.lane_warmup_timeout = mock_settings_fixture.lane_warmup_timeout
        mock_settings.strict_lane_startup = True
        
        mock_wait_for.side_effect = asyncio.TimeoutError()

        with pytest.raises(RuntimeError, match="Lane warmup timed out"):
            await warmup_lanes_at_startup()

    @patch("app.services.vllm_lane_manager.initialize_lane_manager")
    @patch("app.services.vllm_lane_manager.settings")
    @patch("asyncio.wait_for")
    @pytest.mark.asyncio
    async def test_lane_warmup_timeout_graceful_mode(self, mock_wait_for, mock_settings, mock_init_lane, mock_settings_fixture):
        """Test lane warmup timeout in graceful mode logs warning."""
        mock_settings.lane_warmup_timeout = mock_settings_fixture.lane_warmup_timeout
        mock_settings.strict_lane_startup = False
        
        mock_wait_for.side_effect = asyncio.TimeoutError()

        # Should not raise exception in graceful mode
        await warmup_lanes_at_startup()

        mock_wait_for.assert_called_once()

    @patch("app.services.vllm_lane_manager.initialize_lane_manager")
    @patch("app.services.vllm_lane_manager.settings")
    @patch("asyncio.wait_for")
    @pytest.mark.asyncio
    async def test_lane_warmup_failure_strict_mode(self, mock_wait_for, mock_settings, mock_init_lane, mock_settings_fixture):
        """Test lane warmup failure in strict mode raises RuntimeError."""
        mock_settings.lane_warmup_timeout = mock_settings_fixture.lane_warmup_timeout
        mock_settings.strict_lane_startup = True
        
        mock_wait_for.side_effect = Exception("Connection failed")

        with pytest.raises(RuntimeError, match="Lane warmup failed"):
            await warmup_lanes_at_startup()

    @patch("app.services.vllm_lane_manager.initialize_lane_manager")
    @patch("app.services.vllm_lane_manager.settings")
    @patch("asyncio.wait_for")
    @pytest.mark.asyncio
    async def test_lane_warmup_failure_graceful_mode(self, mock_wait_for, mock_settings, mock_init_lane, mock_settings_fixture):
        """Test lane warmup failure in graceful mode logs warning."""
        mock_settings.lane_warmup_timeout = mock_settings_fixture.lane_warmup_timeout
        mock_settings.strict_lane_startup = False
        
        mock_wait_for.side_effect = Exception("Connection failed")

        # Should not raise exception in graceful mode
        await warmup_lanes_at_startup()

        mock_wait_for.assert_called_once()


class TestModelWarmupService:
    """Test the model warmup service functionality."""

    def test_lane_status_extraction(self):
        """Test lane name extraction from URLs."""
        service = model_warmup_service

        # Test various hostname patterns
        assert service._extract_lane_name("http://llama-super-reader:8080/v1") == "super_reader"
        assert service._extract_lane_name("http://governance:8081/v1") == "governance"
        assert service._extract_lane_name("http://inference-vllm:8000/v1") == "orchestrator"
        assert service._extract_lane_name("http://unknown-service:9000/v1") == "unknown_service"

    def test_get_lane_status_unavailable_when_not_monitoring(self):
        """Test that lane status returns unavailable when not monitoring."""
        service = model_warmup_service

        # Ensure not monitoring
        service.stop_monitoring()

        status = service.get_lane_status("http://test:8080/health")
        assert status == "unavailable"

    def test_get_all_lane_statuses_empty_when_no_endpoints(self):
        """Test that get_all_lane_statuses returns empty dict when no endpoints."""
        service = model_warmup_service

        # Clear any endpoints
        service._endpoints = ()
        service._endpoint_status = {}

        statuses = service.get_all_lane_statuses()
        assert statuses == {}
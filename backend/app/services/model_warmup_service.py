from __future__ import annotations

import asyncio
import logging
import threading
from typing import Dict, Literal, Sequence
from urllib.parse import urlparse

import requests

from app.config import Settings

LaneStatus = Literal["healthy", "loading", "unavailable", "error"]


class ModelWarmupService:
    """
    Tracks whether the model lanes have completed their warmup phase.

    A background monitor repeatedly hits each configured /health endpoint until
    all services respond successfully. Until that happens, the backend can surface
    a `warming_up` status to the frontend to explain missing responses.
    """

    def __init__(self, check_interval: float = 5.0, request_timeout: float = 2.0) -> None:
        self._check_interval = check_interval
        self._request_timeout = request_timeout
        self._lock = threading.Lock()
        self._ready: bool = False
        self._last_error: str | None = None
        self._endpoints: tuple[str, ...] = ()
        self._endpoint_status: Dict[str, Dict] = {}
        self._monitor_task: asyncio.Task | None = None
        self._logger = logging.getLogger(__name__)

    def is_ready(self) -> bool:
        with self._lock:
            return self._ready

    def status_reason(self) -> str | None:
        with self._lock:
            return self._last_error

    @property
    def _monitoring_active(self) -> bool:
        """Check if monitoring is currently active."""
        with self._lock:
            return self._monitor_task is not None and not self._monitor_task.done()

    def _mark_ready(self) -> None:
        with self._lock:
            self._ready = True
            self._last_error = None

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._ready = False
            self._last_error = message

    def start_monitoring(self, endpoints: Sequence[str]) -> None:
        normalized = tuple(dict.fromkeys(endpoint for endpoint in endpoints if endpoint))
        if not normalized:
            self._logger.info("No model lane health endpoints configured, marking warmup complete.")
            self._mark_ready()
            return

        with self._lock:
            if self._monitor_task is not None and not self._monitor_task.done():
                self._logger.debug("Model warmup monitor already running.")
                return
            self._ready = False
            self._last_error = "Waiting for model lane health checks..."
            self._endpoints = normalized
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._logger.warning("Cannot start model warmup monitor without running event loop.")
            return
            self._monitor_task = loop.create_task(self._monitor_loop(normalized))

    def get_lane_status(self, endpoint_url: str) -> LaneStatus:
        """Get current status of a lane endpoint."""
        if not self._monitoring_active:
            return "unavailable"

        endpoint_state = self._endpoint_status.get(endpoint_url)
        if not endpoint_state:
            return "unavailable"

        if endpoint_state.get("is_healthy"):
            return "healthy"
        elif endpoint_state.get("is_warming_up"):
            return "loading"
        elif endpoint_state.get("last_error"):
            return "error"
        else:
            return "unavailable"

    def get_all_lane_statuses(self) -> Dict[str, LaneStatus]:
        """Get status of all monitored lanes."""
        statuses = {}
        for endpoint_url in self._endpoints:
            # Extract lane name from URL (e.g., "http://llama-super-reader:8080" -> "super_reader")
            lane_name = self._extract_lane_name(endpoint_url)
            statuses[lane_name] = self.get_lane_status(endpoint_url)
        return statuses

    def _extract_lane_name(self, url: str) -> str:
        """Extract lane name from endpoint URL."""
        # Simple heuristic: extract hostname and convert to snake_case
        from urllib.parse import urlparse
        hostname = urlparse(url).hostname or "unknown"
        if "super-reader" in hostname:
            return "super_reader"
        elif "governance" in hostname:
            return "governance"
        elif "orchestrator" in hostname or "vllm" in hostname:
            return "orchestrator"
        elif "coder" in hostname:
            return "coder"
        elif "fast-rag" in hostname:
            return "fast_rag"
        return hostname.replace("-", "_")

    async def _monitor_loop(self, endpoints: tuple[str, ...]) -> None:
        try:
            while not self.is_ready():
                errors: list[str] = []
                all_healthy = True

                for endpoint in endpoints:
                    success, reason = await asyncio.to_thread(self._probe_endpoint, endpoint)
                    with self._lock:
                        if success:
                            self._endpoint_status[endpoint] = {
                                "is_healthy": True,
                                "is_warming_up": False,
                                "last_error": None,
                            }
                        else:
                            all_healthy = False
                            self._endpoint_status[endpoint] = {
                                "is_healthy": False,
                                "is_warming_up": True,
                                "last_error": reason,
                            }
                            errors.append(f"{endpoint}: {reason}")

                if all_healthy:
                    self._logger.info("Model lanes are healthy.")
                    self._mark_ready()
                    return

                self._set_error("; ".join(errors))
                self._logger.debug("Model warmup pending (%s). Retrying in %.1fs", self._last_error, self._check_interval)
                await asyncio.sleep(self._check_interval)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - best-effort monitor
            self._logger.exception("Model warmup monitor crashed: %s", exc)
            self._set_error("Warmup monitor encountered an error.")
        finally:
            with self._lock:
                self._monitor_task = None

    def _probe_endpoint(self, endpoint: str) -> tuple[bool, str]:
        try:
            response = requests.get(endpoint, timeout=self._request_timeout)
            if 200 <= response.status_code < 300:
                return True, ""
            return False, f"unexpected status {response.status_code}"
        except requests.RequestException as exc:
            return False, str(exc)

    def stop_monitoring(self) -> None:
        """Stop the background monitor task."""
        with self._lock:
            if self._monitor_task is not None:
                self._monitor_task.cancel()
                self._monitor_task = None
        self._logger.info("Model warmup monitor stopped.")


def build_lane_health_endpoints(settings: Settings) -> list[str]:
    lane_urls = [
        settings.lane_orchestrator_url,
        settings.lane_coder_url,
        settings.lane_fast_rag_url,
        settings.lane_super_reader_url,
        settings.lane_governance_url,
    ]
    seen: set[str] = set()
    endpoints: list[str] = []
    for url in lane_urls:
        health_url = _health_endpoint_from_url(url)
        if health_url and health_url not in seen:
            seen.add(health_url)
            endpoints.append(health_url)
    return endpoints


def _health_endpoint_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/health"


model_warmup_service = ModelWarmupService()

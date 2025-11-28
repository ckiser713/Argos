from __future__ import annotations

import asyncio
import logging
import threading
from typing import Sequence
from urllib.parse import urlparse

import requests

from app.config import Settings


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
        self._monitor_task: asyncio.Task | None = None
        self._logger = logging.getLogger(__name__)

    def is_ready(self) -> bool:
        with self._lock:
            return self._ready

    def status_reason(self) -> str | None:
        with self._lock:
            return self._last_error

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

    async def _monitor_loop(self, endpoints: tuple[str, ...]) -> None:
        try:
            while not self.is_ready():
                errors: list[str] = []
                for endpoint in endpoints:
                    success, reason = await asyncio.to_thread(self._probe_endpoint, endpoint)
                    if not success:
                        errors.append(f"{endpoint}: {reason}")

                if not errors:
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

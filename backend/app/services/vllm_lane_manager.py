"""
vLLM Model Lane Manager for sequential model switching.

This service manages loading/unloading vLLM models for different lanes
(ORCHESTRATOR, CODER, FAST_RAG) on a single GPU, queuing requests during
model switches.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import httpx

from app.config import get_settings
from app.domain.model_lanes import ModelLane, is_llama_lane, is_vllm_lane
from app.services.model_registry import (
    get_lane_backend,
    get_lane_default_path,
    get_lane_model_name,
)

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class LaneConfig:
    """Configuration for a model lane."""
    lane: ModelLane
    model_path: str
    url: str
    backend: str  # "vllm" or "llama_cpp"
    model_name: str
    max_model_len: int = 32768
    gpu_memory_utilization: float = 0.45


@dataclass
class QueuedRequest:
    """A request waiting for model switch to complete."""
    lane: ModelLane
    callback: Callable[[], Any]
    future: asyncio.Future = field(default_factory=asyncio.Future)
    queued_at: float = field(default_factory=time.time)


class VLLMLaneManager:
    """
    Manages vLLM model lanes with sequential switching.
    
    - Tracks currently loaded model
    - Queues requests during model switches (30-60s)
    - Preloads ORCHESTRATOR at startup
    - SUPER_READER/GOVERNANCE use separate llama-server instances (always available)
    """
    
    # vLLM lanes that share the same GPU and require switching
    VLLM_LANES = {ModelLane.ORCHESTRATOR, ModelLane.CODER, ModelLane.FAST_RAG}
    
    # llama.cpp lanes run on dedicated servers (no switching needed)
    LLAMA_CPP_LANES = {ModelLane.SUPER_READER, ModelLane.GOVERNANCE}
    
    def __init__(self):
        self._current_lane: Optional[ModelLane] = None
        self._is_switching: bool = False
        self._switch_lock = asyncio.Lock()
        self._request_queue: list[QueuedRequest] = []
        self._queue_event: Optional[asyncio.Event] = None
        self._queue_worker_task: Optional[asyncio.Task] = None
        self._lane_configs = self._build_lane_configs()
        self._vllm_base_url = self._normalize_base_url(settings.lane_orchestrator_url)
        self._http_client: Optional[httpx.AsyncClient] = None

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        if not url:
            return ""
        normalized = url.rstrip("/")
        if normalized.endswith("/v1"):
            return normalized[:-3]
        return normalized

    def _build_lane_configs(self) -> dict[ModelLane, LaneConfig]:
        """Build lane configurations from settings."""
        return {
            ModelLane.ORCHESTRATOR: LaneConfig(
                lane=ModelLane.ORCHESTRATOR,
                model_path=settings.lane_orchestrator_model_path or get_lane_default_path(ModelLane.ORCHESTRATOR),
                url=settings.lane_orchestrator_url,
                backend=settings.lane_orchestrator_backend or get_lane_backend(ModelLane.ORCHESTRATOR),
                model_name=settings.lane_orchestrator_model or get_lane_model_name(ModelLane.ORCHESTRATOR),
                max_model_len=32768,
                gpu_memory_utilization=0.45,
            ),
            ModelLane.CODER: LaneConfig(
                lane=ModelLane.CODER,
                model_path=settings.lane_coder_model_path or get_lane_default_path(ModelLane.CODER),
                url=settings.lane_coder_url,
                backend=settings.lane_coder_backend or get_lane_backend(ModelLane.CODER),
                model_name=settings.lane_coder_model or get_lane_model_name(ModelLane.CODER),
                max_model_len=32768,
                gpu_memory_utilization=0.45,
            ),
            ModelLane.FAST_RAG: LaneConfig(
                lane=ModelLane.FAST_RAG,
                model_path=settings.lane_fast_rag_model_path or get_lane_default_path(ModelLane.FAST_RAG),
                url=settings.lane_fast_rag_url,
                backend=settings.lane_fast_rag_backend or get_lane_backend(ModelLane.FAST_RAG),
                model_name=settings.lane_fast_rag_model or get_lane_model_name(ModelLane.FAST_RAG),
                max_model_len=131072,  # 128k context for RAG
                gpu_memory_utilization=0.45,
            ),
            ModelLane.SUPER_READER: LaneConfig(
                lane=ModelLane.SUPER_READER,
                model_path=settings.lane_super_reader_model_path or get_lane_default_path(ModelLane.SUPER_READER),
                url=settings.lane_super_reader_url,
                backend=settings.lane_super_reader_backend or get_lane_backend(ModelLane.SUPER_READER),
                model_name=settings.lane_super_reader_model or get_lane_model_name(ModelLane.SUPER_READER),
            ),
            ModelLane.GOVERNANCE: LaneConfig(
                lane=ModelLane.GOVERNANCE,
                model_path=settings.lane_governance_model_path or get_lane_default_path(ModelLane.GOVERNANCE),
                url=settings.lane_governance_url,
                backend=settings.lane_governance_backend or get_lane_backend(ModelLane.GOVERNANCE),
                model_name=settings.lane_governance_model or get_lane_model_name(ModelLane.GOVERNANCE),
            ),
        }
    
    @property
    def current_lane(self) -> Optional[ModelLane]:
        """Get the currently loaded vLLM lane."""
        return self._current_lane
    
    @property
    def is_switching(self) -> bool:
        """Check if a model switch is in progress."""
        return self._is_switching
    
    def get_lane_config(self, lane: ModelLane) -> LaneConfig:
        """Get configuration for a lane."""
        return self._lane_configs[lane]
    
    def get_lane_url(self, lane: ModelLane) -> str:
        """Get the API URL for a lane."""
        return self._lane_configs[lane].url

    async def ensure_lane(self, lane: ModelLane) -> bool:
        """Ensure the requested lane is loaded and ready for vLLM."""
        if is_llama_lane(lane):
            return True
        if self._current_lane == lane and not self._is_switching:
            return True
        return await self.switch_model(lane)
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client
    
    async def _check_vllm_health(self) -> bool:
        """Check if vLLM server is healthy."""
        try:
            client = await self._get_http_client()
            response = await client.get(f"{self._vllm_base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def is_vllm_healthy(self) -> bool:
        """Expose vLLM health check for callers."""
        return await self._check_vllm_health()
    
    async def _get_current_vllm_model(self) -> Optional[str]:
        """Get the currently loaded model from vLLM."""
        try:
            client = await self._get_http_client()
            response = await client.get(f"{self._vllm_base_url}/v1/models")
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    return data["data"][0].get("id")
        except Exception as e:
            logger.warning(f"Failed to get current vLLM model: {e}")
        return None
    
    async def initialize(self, default_lane: ModelLane = ModelLane.ORCHESTRATOR):
        """
        Initialize the lane manager and preload the default model.
        
        Called at backend startup to ensure ORCHESTRATOR is ready.
        """
        logger.info(f"Initializing VLLMLaneManager with default lane: {default_lane}")
        
        # Check if vLLM is already running with a model
        if await self._check_vllm_health():
            current_model = await self._get_current_vllm_model()
            if current_model:
                # Try to match current model to a lane
                for lane, config in self._lane_configs.items():
                    if lane in self.VLLM_LANES and config.model_path in current_model:
                        self._current_lane = lane
                        logger.info(f"vLLM already running with lane: {lane}")
                        return
        
        # Load default lane
        await self.switch_model(default_lane)
        self._ensure_queue_worker()

    def _ensure_queue_worker(self) -> None:
        if self._queue_worker_task is not None and not self._queue_worker_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("Cannot start vLLM queue worker without a running event loop.")
            return
        self._queue_event = asyncio.Event()
        self._queue_worker_task = loop.create_task(self._queue_worker())
    
    async def switch_model(self, target_lane: ModelLane) -> bool:
        """
        Switch vLLM to load a different model.
        
        For llama.cpp lanes (SUPER_READER, GOVERNANCE), this is a no-op
        since they run on dedicated servers.
        
        Returns True if switch was successful or no switch needed.
        """
        # llama.cpp lanes don't need switching
        if target_lane in self.LLAMA_CPP_LANES:
            logger.debug(f"Lane {target_lane} uses llama-server, no switch needed")
            return True
        
        # Check if already on target lane
        if self._current_lane == target_lane:
            logger.debug(f"Already on lane {target_lane}")
            return True
        
        async with self._switch_lock:
            # Double-check after acquiring lock
            if self._current_lane == target_lane:
                return True
            
            self._is_switching = True
            config = self._lane_configs[target_lane]
            
            logger.info(
                f"Switching vLLM model: {self._current_lane} -> {target_lane}",
                extra={"model_path": config.model_path}
            )
            
            start_time = time.time()
            
            try:
                # vLLM doesn't have hot-reload API yet, so we need to:
                # 1. Signal vLLM to reload (via env var change + SIGHUP, or restart)
                # 2. Wait for model to load
                # 3. Verify health
                
                # For now, we'll use the /v1/models endpoint to check
                # In production, this would trigger a container restart or
                # use vLLM's future model switching API
                
                # Simulate model switch time (remove in production)
                # In reality, this would be an actual model reload
                did_reload = await self._reload_vllm_model(config)
                
                if not did_reload and settings.argos_env == "local":
                    logger.info("Skipping model load wait in local dev mode")
                    self._current_lane = target_lane
                    return True

                # Wait for health check
                max_wait = 120  # 2 minutes max
                wait_interval = 5
                waited = 0
                
                while waited < max_wait:
                    if await self._check_vllm_health():
                        current = await self._get_current_vllm_model()
                        if current and config.model_path in current:
                            break
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    logger.debug(f"Waiting for vLLM model load... ({waited}s)")
                
                if waited >= max_wait:
                    logger.error(f"Timeout waiting for model switch to {target_lane}")
                    return False
                
                self._current_lane = target_lane
                elapsed = time.time() - start_time
                
                logger.info(
                    f"Model switch complete: {target_lane}",
                    extra={"elapsed_seconds": elapsed}
                )
                
                return True
                
            except Exception as e:
                logger.exception(f"Error switching to lane {target_lane}: {e}")
                return False
            
            finally:
                self._is_switching = False
    
    async def _reload_vllm_model(self, config: LaneConfig) -> bool:
        """
        Trigger vLLM to reload with a new model via Docker API.
        
        Restarts the vLLM container with updated environment variables
        to load the new model.
        """
        import os
        
        logger.info(
            f"Reloading vLLM with model: {config.model_path}",
            extra={
                "model_name": config.model_name,
                "max_model_len": config.max_model_len,
                "gpu_memory_utilization": config.gpu_memory_utilization,
            }
        )
        
        # Check if we're in Docker environment or local
        in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_HOST")
        
        use_docker_switching = os.environ.get("ARGOS_USE_DOCKER_SWITCHING", "").lower() == "true"
        cortex_switching = os.environ.get("CORTEX_USE_DOCKER_SWITCHING", "").lower() == "true"
        if cortex_switching and not os.environ.get("ARGOS_USE_DOCKER_SWITCHING"):
            logger.warning(
                "CORTEX_USE_DOCKER_SWITCHING is deprecated; use ARGOS_USE_DOCKER_SWITCHING instead."
            )
        if in_docker or use_docker_switching or cortex_switching:
            try:
                import docker
                client = docker.from_env()
                
                container_name = "argos-vllm-service"
                
                try:
                    container = client.containers.get(container_name)
                    
                    # Update environment with new model path
                    new_env = {
                        "ARGOS_VLLM_MODEL": config.model_path,
                        "CORTEX_VLLM_MODEL": config.model_path,
                        "VLLM_MAX_MODEL_LEN": str(config.max_model_len),
                        "VLLM_GPU_MEMORY_UTILIZATION": str(config.gpu_memory_utilization),
                    }
                    
                    logger.info(f"Stopping vLLM container for model switch...")
                    container.stop(timeout=30)
                    container.wait()
                    
                    # Get current container config and update
                    old_env = container.attrs.get("Config", {}).get("Env", [])
                    env_dict = dict(e.split("=", 1) for e in old_env if "=" in e)
                    env_dict.update(new_env)
                    
                    # Remove old container
                    container.remove()
                    
                    # Start new container with updated model
                    logger.info(f"Starting vLLM container with model: {config.model_path}")
                    client.containers.run(
                        image=container.image.tags[0] if container.image.tags else "vllm-rocm-strix:latest",
                        name=container_name,
                        detach=True,
                        environment=env_dict,
                        volumes=container.attrs.get("HostConfig", {}).get("Binds", []),
                        device_requests=container.attrs.get("HostConfig", {}).get("DeviceRequests", []),
                        ports={"8000/tcp": 8000},
                        network="argos-network",
                        shm_size="16g",
                    )
                    
                    logger.info(f"vLLM container restarted with new model")
                    return True
                    
                except docker.errors.NotFound:
                    logger.warning(f"Container {container_name} not found, skipping Docker switch")
                    return False
                    
            except ImportError:
                logger.warning("Docker package not installed, skipping Docker-based switching")
                return False
            except Exception as e:
                logger.error(f"Docker switching failed: {e}")
                return False
        else:
            # Local development mode - just log the intended action
            logger.info(
                f"[DEV MODE] Would reload vLLM with model: {config.model_path}",
                extra={
                    "note": "Set ARGOS_USE_DOCKER_SWITCHING=true to enable Docker switching",
                }
            )
            return False

    async def _queue_worker(self) -> None:
        if not self._queue_event:
            return
        while True:
            await self._queue_event.wait()
            self._queue_event.clear()
            while self._request_queue:
                request = self._request_queue.pop(0)
                try:
                    if is_vllm_lane(request.lane):
                        if not await self.ensure_lane(request.lane):
                            raise RuntimeError(f"Failed to load lane {request.lane}")
                    result = request.callback()
                    if asyncio.iscoroutine(result):
                        result = await result
                    request.future.set_result(result)
                except Exception as exc:
                    if not request.future.done():
                        request.future.set_exception(exc)
    
    async def queue_request(
        self,
        lane: ModelLane,
        callback: Callable[[], Any],
    ) -> asyncio.Future:
        """
        Queue a request to be processed when the target lane is loaded.
        
        If the lane is already loaded, executes immediately.
        If a switch is needed, queues the request and triggers switch.
        """
        # llama.cpp lanes are always available
        if is_llama_lane(lane) or (self._current_lane == lane and not self._is_switching):
            future = asyncio.Future()
            try:
                result = callback()
                if asyncio.iscoroutine(result):
                    result = await result
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            return future
        
        # Queue the request
        request = QueuedRequest(lane=lane, callback=callback)
        self._request_queue.append(request)

        self._ensure_queue_worker()
        if self._queue_event:
            self._queue_event.set()

        return request.future
    
    def get_status(self) -> dict:
        """Get current lane manager status."""
        return {
            "current_lane": self._current_lane.value if self._current_lane else None,
            "is_switching": self._is_switching,
            "queued_requests": len(self._request_queue),
            "vllm_lanes": [l.value for l in self.VLLM_LANES],
            "llama_cpp_lanes": [l.value for l in self.LLAMA_CPP_LANES],
            "lane_configs": {
                lane.value: {
                    "url": config.url,
                    "model_name": config.model_name,
                    "backend": config.backend,
                }
                for lane, config in self._lane_configs.items()
            },
        }
    
    async def close(self):
        """Cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
        if self._queue_worker_task:
            self._queue_worker_task.cancel()
            try:
                await self._queue_worker_task
            except asyncio.CancelledError:
                pass


# Global singleton instance
_lane_manager: Optional[VLLMLaneManager] = None


def get_lane_manager() -> VLLMLaneManager:
    """Get or create the global lane manager instance."""
    global _lane_manager
    if _lane_manager is None:
        _lane_manager = VLLMLaneManager()
    return _lane_manager


async def initialize_lane_manager(default_lane: ModelLane = ModelLane.ORCHESTRATOR):
    """Initialize the lane manager at startup."""
    manager = get_lane_manager()
    await manager.initialize(default_lane)
    return manager


async def warmup_lanes_at_startup() -> None:
    """Warm up the vLLM lane manager and preload the default lane with timeout and graceful degradation."""
    timeout = settings.lane_warmup_timeout
    strict = settings.strict_lane_startup

    logger.info(
        f"Initializing lane switching (timeout={timeout}s, strict={strict})",
        extra={"event": "lane.warmup.start"},
    )

    try:
        # Wrap with timeout
        await asyncio.wait_for(
            initialize_lane_manager(ModelLane.ORCHESTRATOR),
            timeout=timeout,
        )
        logger.info(
            "Lane warmup completed successfully",
            extra={"event": "lane.warmup.success"},
        )
    except asyncio.TimeoutError:
        msg = f"Lane warmup timed out after {timeout}s"
        logger.error(msg, extra={"event": "lane.warmup.timeout"})
        if strict:
            raise RuntimeError(
                f"{msg}. Set ARGOS_STRICT_LANE_STARTUP=false to continue with degraded lanes."
            )
        else:
            logger.warning(
                "Continuing with degraded lane availability (strict_lane_startup=false)",
                extra={"event": "lane.warmup.degraded"},
            )
    except Exception as exc:
        msg = f"Lane warmup failed: {exc}"
        logger.error(msg, extra={"event": "lane.warmup.error", "error": str(exc)})
        if strict:
            raise RuntimeError(
                f"{msg}. Set ARGOS_STRICT_LANE_STARTUP=false to continue without lanes."
            )
        else:
            logger.warning(
                "Continuing without lane initialization (strict_lane_startup=false)",
                extra={"event": "lane.warmup.degraded", "error": str(exc)},
            )

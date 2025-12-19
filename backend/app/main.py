import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

from app.api.routes import (
    agents,
    auth,
    context,
    gap_analysis,
    health,
    ideas,
    ingest,
    knowledge,
    mode,
    n8n,
    project_intel,
    projects,
    roadmap,
    streaming,
    system,
    workflows,
)
from app.config import get_settings
from app.db import init_db
from app.domain.model_lanes import ModelLane
from app.observability import (
    ObservabilityMiddleware,
    configure_logging,
    setup_metrics_endpoint,
    setup_tracing,
)
from app.services.auth_service import get_current_user
from app.services.model_warmup_service import build_lane_health_endpoints, model_warmup_service
from app.services.qdrant_service import qdrant_service
from app.services.vllm_lane_manager import initialize_lane_manager, warmup_lanes_at_startup

# ... (rest of the imports)


def _env_flag(name: str) -> bool:
    """Return True when an environment variable is set to a truthy value."""
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_uvicorn_pid1() -> bool:
    """Detect if uvicorn is running as PID 1 (common in containers/systemd)."""
    if os.getpid() == 1:
        return True
    try:
        comm_path = Path("/proc/1/comm")
        if comm_path.exists() and "uvicorn" in comm_path.read_text():
            return True
        cmdline_path = Path("/proc/1/cmdline")
        if cmdline_path.exists() and "uvicorn" in cmdline_path.read_text():
            return True
    except Exception:
        # Fall back silently if /proc is unavailable
        pass
    return False


def validate_runtime_prereqs(settings, logger) -> None:
    """
    Enforce startup rules for non-local environments.
    
    Allows container/systemd runs via RUNNING_IN_DOCKER=1 or uvicorn PID 1.
    Bare-metal non-local runs must be inside nix (IN_NIX_SHELL), unless explicitly
    overridden via CORTEX_ALLOW_NON_NIX=1.
    """
    logger.info(f"Checking runtime guard for {settings.argos_env}")

    if settings.argos_env == "local":
        logger.info("Local environment, skipping nix check.")
        return

    normalized_db = (settings.database_url or "").lower()
    if not normalized_db.startswith("postgresql"):
        raise RuntimeError(
            "CORTEX_DATABASE_URL must point to Postgres (postgresql://...) when CORTEX_ENV "
            "is not local. SQLite is only supported for local development."
        )

    if os.environ.get("IN_NIX_SHELL"):
        logger.info("Nix environment check passed.")
        return

    if _env_flag("CORTEX_ALLOW_NON_NIX"):
        logger.warning("CORTEX_ALLOW_NON_NIX=1 set; bypassing Nix shell enforcement.")
        return

    if _env_flag("RUNNING_IN_DOCKER") or _is_uvicorn_pid1():
        logger.info("Container/systemd environment detected; nix shell enforcement relaxed.")
        return

    raise RuntimeError(
        "Non-local environments must run within a Nix shell. Set IN_NIX_SHELL=1 when running "
        "on bare metal, or set RUNNING_IN_DOCKER=1 (container) or CORTEX_ALLOW_NON_NIX=1 "
        "to bypass this guard for container/systemd deployments."
    )


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings)
    logger = logging.getLogger(__name__)
    validate_runtime_prereqs(settings, logger)
    init_db()
    logger.info("==================================================")
    logger.info("    Argos Backend Service Booting Up")
    logger.info("==================================================")
    logger.info(f"CORTEX_ENV: {settings.argos_env}")
    logger.info(f"LLM Backend: {settings.llm_backend}")
    logger.info("--- Lane URLs ---")
    logger.info(f"  Orchestrator: {settings.lane_orchestrator_url}")
    logger.info(f"  Coder: {settings.lane_coder_url}")
    logger.info(f"  Super Reader: {settings.lane_super_reader_url}")
    logger.info(f"  Fast RAG: {settings.lane_fast_rag_url}")
    logger.info(f"  Governance: {settings.lane_governance_url}")
    logger.info("-------------------")
    if settings.argos_env != "local" and any("localhost" in origin for origin in settings.allowed_origins):
        logger.warning(
            "CORTEX_ALLOWED_ORIGINS includes localhost while running in non-local environment; set it to your frontend domain."
        )
    # --- End Startup Logging ---

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    setup_metrics_endpoint(app)
    
    # CORS for local frontend dev - must be added before other middlewares
    # Support multiple ports for development flexibility
    allowed = settings.allowed_origins if settings.allowed_origins_str.strip() != "*" else [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(ObservabilityMiddleware)

    # ... (rest of the create_app function)

    setup_tracing(app, settings)

    @app.on_event("startup")
    def check_runtime_environment() -> None:
        """Verify runtime guard when the application starts."""
        validate_runtime_prereqs(get_settings(), logger)

    @app.on_event("startup")
    def verify_embedding_stack() -> None:
        """Fail fast when embeddings are required but unavailable."""
        try:
            health = qdrant_service.ensure_ready(require_embeddings=settings.require_embeddings)
            if not health.get("can_generate_embeddings"):
                logger.warning(
                    "Embedding models unavailable; falling back to text-only search and degraded RAG.",
                    extra={"event": "embeddings.health.warning"},
                )
        except Exception as exc:
            logger.critical(
                "Embedding/Qdrant startup check failed: %s",
                exc,
                extra={"event": "embeddings.health.failed"},
            )
            raise

    # Skip auth in test environment
    if settings.debug or getattr(settings, 'skip_auth', False):
        auth_deps = []
    else:
        auth_deps = [Depends(get_current_user)]

    @app.on_event("startup")
    async def initialize_lane_switching() -> None:
        """Warm up the vLLM lane manager and preload the default lane with timeout and graceful degradation."""
        await warmup_lanes_at_startup()

    @app.on_event("startup")
    async def initialize_warmup_monitor() -> None:
        """Initialize model warmup monitoring for production environments."""
        if settings.argos_env in ["strix", "production"]:
            logger.info("Initializing model warmup monitoring...")
            endpoints = build_lane_health_endpoints(settings)
            model_warmup_service.start_monitoring(endpoints)
            logger.info(f"Warmup monitoring started for {len(endpoints)} endpoints")
        else:
            logger.info("Skipping warmup monitoring in local environment")

    @app.on_event("shutdown")
    async def shutdown_warmup_monitor() -> None:
        """Stop warmup monitoring on shutdown."""
        model_warmup_service.stop_monitoring()
        logger.info("Warmup monitoring stopped")

    # Routers grouped by resource
    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(health.router, tags=["health"])
    app.include_router(system.router, prefix="/api", tags=["system"], dependencies=auth_deps)
    app.include_router(projects.router, prefix="/api", tags=["projects"], dependencies=auth_deps)
    app.include_router(context.router, prefix="/api", tags=["context"], dependencies=auth_deps)
    app.include_router(workflows.router, prefix="/api", tags=["workflows"], dependencies=auth_deps)
    app.include_router(ingest.router, prefix="/api", tags=["ingest"], dependencies=auth_deps)
    app.include_router(agents.router, prefix="/api", tags=["agents"], dependencies=auth_deps)
    app.include_router(knowledge.router, prefix="/api", tags=["knowledge"], dependencies=auth_deps)
    app.include_router(streaming.router, prefix="/api/stream", tags=["streaming"], dependencies=auth_deps)
    app.include_router(ideas.router, prefix="/api", tags=["ideas"], dependencies=auth_deps)
    app.include_router(project_intel.router, prefix="/api", tags=["project-intel"], dependencies=auth_deps)
    app.include_router(mode.router, prefix="/api", tags=["mode"], dependencies=auth_deps)
    app.include_router(gap_analysis.router, prefix="/api", tags=["gap-analysis"], dependencies=auth_deps)
    app.include_router(roadmap.router, prefix="/api", tags=["roadmap"], dependencies=auth_deps)
    # (ideas router already included above)
    app.include_router(n8n.router, prefix="/api", tags=["n8n"], dependencies=auth_deps)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

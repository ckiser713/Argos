import logging
import os

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
from app.services.auth_service import verify_token
from app.services.model_warmup_service import build_lane_health_endpoints, model_warmup_service

# ... (rest of the imports)

def create_app() -> FastAPI:
    settings = get_settings()
    init_db()

    # --- Startup Logging ---
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("==================================================")
    logger.info("    Cortex Backend Service Booting Up")
    logger.info("==================================================")
    logger.info(f"CORTEX_ENV: {settings.cortex_env}")
    logger.info(f"LLM Backend: {settings.llm_backend}")
    logger.info("--- Lane URLs ---")
    logger.info(f"  Orchestrator: {settings.lane_orchestrator_url}")
    logger.info(f"  Coder: {settings.lane_coder_url}")
    logger.info(f"  Super Reader: {settings.lane_super_reader_url}")
    logger.info(f"  Fast RAG: {settings.lane_fast_rag_url}")
    logger.info(f"  Governance: {settings.lane_governance_url}")
    logger.info("-------------------")
    # --- End Startup Logging ---

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # ... (rest of the create_app function)


    # CORS for local frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def check_nix_environment():
        """Verify that non-local environments run inside Nix shell."""
        settings = get_settings()
        logger.info(f"Checking nix environment for {settings.cortex_env}")
        if settings.cortex_env != "local":
            if not os.environ.get("IN_NIX_SHELL"):
                logger.critical("CRITICAL: Non-local environment started outside of Nix shell.")
                raise RuntimeError(
                    "FATAL: Non-local environments must be run within the Nix shell. "
                    "Set IN_NIX_SHELL environment variable or run via 'nix develop'."
                )
            else:
                logger.info("Nix environment check passed.")
        else:
            logger.info("Local environment, skipping nix check.")

    # Skip auth in test environment
    if settings.debug or getattr(settings, 'skip_auth', False):
        auth_deps = []
    else:
        auth_deps = [Depends(verify_token)]

    @app.on_event("startup")
    async def initialize_warmup_monitor() -> None:
        """Initialize model warmup monitoring for production environments."""
        if settings.cortex_env in ["strix", "production"]:
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

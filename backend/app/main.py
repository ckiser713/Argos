from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import (
    system,
    context,
    workflows,
    ingest,
    agents,
    knowledge,
    streaming,
    project_intel,
    mode,
    gap_analysis,
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS for local frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers grouped by resource
    app.include_router(system.router, prefix="/api", tags=["system"]) # system.router already has prefix /system
    app.include_router(context.router, prefix="/api/context", tags=["context"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
    app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
    app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
    app.include_router(knowledge.router, prefix="/api/knowledge", tags=["knowledge"])
    app.include_router(streaming.router, prefix="/api/stream", tags=["streaming"])
    app.include_router(project_intel.router, prefix="/api", tags=["project-intel"]) # project_intel.router already has prefix /projects
    app.include_router(mode.router, prefix="/api", tags=["mode"]) # mode.router already has prefix /projects
    app.include_router(gap_analysis.router, prefix="/api", tags=["gap-analysis"])


    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

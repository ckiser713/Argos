from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    agents,
    auth,
    context,
    gap_analysis,
    ideas,
    ingest,
    knowledge,
    mode,
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


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()

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

    # Skip auth in test environment
    if settings.debug or getattr(settings, 'skip_auth', False):
        auth_deps = []
    else:
        auth_deps = [Depends(verify_token)]

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
    app.include_router(project_intel.router, prefix="/api", tags=["project-intel"], dependencies=auth_deps)
    app.include_router(mode.router, prefix="/api", tags=["mode"], dependencies=auth_deps)
    app.include_router(gap_analysis.router, prefix="/api", tags=["gap-analysis"], dependencies=auth_deps)
    app.include_router(roadmap.router, prefix="/api", tags=["roadmap"], dependencies=auth_deps)
    app.include_router(ideas.router, prefix="/api", tags=["ideas"], dependencies=auth_deps)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

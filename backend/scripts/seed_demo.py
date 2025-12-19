#!/usr/bin/env python3
"""
Seed a tiny demo workspace, ingest a few fixture documents, and optionally
create a non-sensitive demo user plus run a smoke-query against the minimal
model flow.

Usage:
    poetry run python scripts/seed_demo.py [--with-demo-user] [--smoke-query "demo"]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

# Ensure backend package is importable when executed from repo root
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db import init_db
from app.domain.models import IngestRequest
from app.domain.project import CreateProjectRequest
from app.models import AuthUser
from app.services.auth_service import create_user, public_user
from app.services.ingest_service import ingest_service
from app.services.project_service import get_project_service
from app.services.qdrant_service import qdrant_service
from app.services.rag_service import rag_service
from app.database import get_async_db_session

FIXTURES_DIR = BACKEND_ROOT / "fixtures" / "demo_docs"


@dataclass
class SeedResult:
    project_id: str
    project_slug: str
    created_jobs: List[str]
    processed_jobs: List[str]
    demo_user: dict | None
    smoke_results: dict | None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo workspace and ingest fixtures.")
    parser.add_argument("--project-name", default="Cortex Demo", help="Name for the demo project.")
    parser.add_argument("--project-slug", default="cortex-demo", help="Slug for the demo project.")
    parser.add_argument(
        "--with-demo-user",
        action="store_true",
        help="Create a demo user (non-production).",
    )
    parser.add_argument("--demo-username", default="demo", help="Username for the demo user.")
    parser.add_argument("--demo-password", default="demo1234", help="Password for the demo user (non-sensitive).")
    parser.add_argument(
        "--skip-processing",
        action="store_true",
        help="Only queue ingest jobs; do not run the pipeline.",
    )
    parser.add_argument(
        "--smoke-query",
        default="What does the ingest pipeline do in this workspace?",
        help="Optional RAG search query to verify embed+LLM wiring.",
    )
    return parser.parse_args()


def _collect_fixture_paths() -> List[Path]:
    if not FIXTURES_DIR.exists():
        raise FileNotFoundError(f"Fixture directory not found: {FIXTURES_DIR}")
    return sorted([p for p in FIXTURES_DIR.iterdir() if p.is_file()])


def _get_or_create_project(name: str, slug: str, description: str | None) -> Tuple[str, str]:
    service = get_project_service()
    existing = service.repo.get_by_slug(slug)
    if existing:
        print(f"Using existing project '{existing.name}' ({existing.id})")
        return existing.id, existing.slug
    project = service.create_project(CreateProjectRequest(name=name, slug=slug, description=description))
    print(f"Created project '{project.name}' ({project.id}) with slug '{project.slug}'")
    return project.id, project.slug


async def _ensure_demo_user(username: str, password: str) -> dict:
    async with get_async_db_session() as session:
        existing = (await session.execute(select(AuthUser).where(AuthUser.username == username))).scalar_one_or_none()
        if existing:
            print(f"Demo user '{username}' already exists; leaving as-is.")
            return public_user(existing)

        user = await create_user(session, username, password, roles=["admin"], scopes=["*"], is_active=True)
        print(f"Created demo user '{username}' (admin role).")
        return public_user(user)


async def _process_job(job_id: str) -> None:
    await ingest_service.process_job(job_id, mark_failed=False)


def seed_ingest_jobs(project_id: str, process: bool) -> Tuple[List[str], List[str]]:
    created: List[str] = []
    processed: List[str] = []
    fixtures = _collect_fixture_paths()

    for path in fixtures:
        request = IngestRequest(source_path=str(path), original_filename=path.name)
        job = ingest_service.create_job(project_id=project_id, request=request)
        created.append(job.id)
        print(f"Created ingest job {job.id} for {path.name}")

        if process:
            try:
                asyncio.run(_process_job(job.id))
                processed.append(job.id)
                print(f"  ✓ processed {path.name}")
            except Exception as exc:  # noqa: BLE001
                print(f"  ✗ failed to process {path.name}: {exc}")
    return created, processed


def run_smoke_query(project_id: str, query: str) -> dict:
    try:
        qdrant_service.ensure_ready(require_embeddings=False)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Qdrant/embeddings not fully ready ({exc}); continuing.")
    try:
        result = rag_service.search(project_id=project_id, query=query, limit=3, use_advanced=False)
        found = result.get("results", []) if isinstance(result, dict) else []
        print(f"Smoke query returned {len(found)} result(s).")
        return result
    except Exception as exc:  # noqa: BLE001
        print(f"Smoke query failed: {exc}")
        return {"error": str(exc)}


def main() -> SeedResult:
    args = _parse_args()
    init_db()

    project_id, project_slug = _get_or_create_project(
        name=args.project_name,
        slug=args.project_slug,
        description="Demo workspace for minimal-model smoke tests.",
    )

    demo_user = None
    if args.with_demo_user:
        demo_user = asyncio.run(_ensure_demo_user(args.demo_username, args.demo_password))

    created_jobs, processed_jobs = seed_ingest_jobs(project_id, process=not args.skip_processing)
    smoke_results = run_smoke_query(project_id, args.smoke_query) if args.smoke_query else None

    return SeedResult(
        project_id=project_id,
        project_slug=project_slug,
        created_jobs=created_jobs,
        processed_jobs=processed_jobs,
        demo_user=demo_user,
        smoke_results=smoke_results,
    )


if __name__ == "__main__":
    result = main()
    print("\n=== Seed Summary ===")
    print(f"Project: {result.project_id} (slug: {result.project_slug})")
    print(f"Created jobs:   {len(result.created_jobs)}")
    print(f"Processed jobs: {len(result.processed_jobs)}")
    if result.demo_user:
        print(f"Demo user: {result.demo_user}")
    if result.smoke_results:
        meta = result.smoke_results.get("query_metadata", {}) if isinstance(result.smoke_results, dict) else {}
        print(f"Smoke query metadata: {meta}")


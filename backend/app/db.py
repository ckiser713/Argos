from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.atlas_db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create base tables required for atlas.db if they do not exist."""
    with db_session() as conn:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                default_model_role_id TEXT,
                root_idea_cluster_id TEXT,
                roadmap_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

            CREATE TABLE IF NOT EXISTS ingest_sources (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                uri TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ingest_sources_project ON ingest_sources(project_id);

            CREATE TABLE IF NOT EXISTS ingest_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                byte_size INTEGER NOT NULL DEFAULT 0,
                mime_type TEXT,
                is_deep_scan INTEGER NOT NULL DEFAULT 0,
                stage TEXT NOT NULL,
                progress REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                canonical_document_id TEXT,
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(source_id) REFERENCES ingest_sources(id)
            );
            CREATE INDEX IF NOT EXISTS idx_ingest_jobs_project ON ingest_jobs(project_id);
            CREATE INDEX IF NOT EXISTS idx_ingest_jobs_source ON ingest_jobs(source_id);
            """
        )
        conn.commit()

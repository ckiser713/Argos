from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db import _is_using_postgresql, db_session, init_db


def test_db_session_accepts_qmark_sql_under_postgres() -> None:
    """Ensure legacy '?' SQL works against PostgreSQL via db_session wrapper."""
    assert _is_using_postgresql(), "This test expects a PostgreSQL database URL"
    init_db()

    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db_session() as conn:
        conn.execute(
            "INSERT INTO projects (id, slug, name, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                project_id,
                f"slug-{project_id[:8]}",
                "Postgres Smoke",
                "active",
                now,
                now,
            ),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

    assert row is not None
    assert row["id"] == project_id
    assert row["slug"].startswith("slug-")


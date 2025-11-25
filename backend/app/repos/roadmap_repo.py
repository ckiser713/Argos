from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from app.db import db_session
from app.domain.project import Roadmap


def save_roadmap(roadmap: Roadmap) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO roadmaps
            (id, project_id, name, graph_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                roadmap.id,
                roadmap.project_id,
                roadmap.name,
                json.dumps(roadmap.graph),
                roadmap.created_at.isoformat(),
                roadmap.updated_at.isoformat(),
            ),
        )
        conn.commit()


def get_roadmap(roadmap_id: str) -> Optional[Roadmap]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,)).fetchone()
        if row:
            return Roadmap(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                graph=json.loads(row["graph_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
    return None


def get_roadmaps_for_project(project_id: str) -> list[Roadmap]:
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM roadmaps WHERE project_id = ?", (project_id,)).fetchall()
        return [
            Roadmap(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                graph=json.loads(row["graph_json"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

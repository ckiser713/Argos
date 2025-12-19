from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import List, Optional

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.project import ArgosProject


class ProjectRepository:
    def list_projects(self, *, cursor: Optional[str], limit: int) -> PaginatedResponse:
        offset = int(cursor) if cursor else 0
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM projects
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit + 1, offset),
            ).fetchall()
            items = [self._row_to_model(row) for row in rows[:limit]]
            next_cursor = str(offset + limit) if len(rows) > limit else None
            total_row = conn.execute("SELECT COUNT(*) as count FROM projects").fetchone()
            total = int(total_row["count"]) if total_row else None
        return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def get_project(self, project_id: str) -> Optional[ArgosProject]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            return self._row_to_model(row)

    def get_by_slug(self, slug: str) -> Optional[ArgosProject]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
            if not row:
                return None
            return self._row_to_model(row)

    def save(self, project: ArgosProject) -> ArgosProject:
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, slug, name, description, status, created_at, updated_at,
                    default_model_role_id, root_idea_cluster_id, roadmap_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.slug,
                    project.name,
                    project.description,
                    project.status,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                    project.default_model_role_id,
                    project.root_idea_cluster_id,
                    project.roadmap_id,
                ),
            )
            conn.commit()
        return project

    def update(self, project_id: str, *, fields: dict) -> Optional[ArgosProject]:
        if not fields:
            return self.get_project(project_id)
        allowed = {
            "name",
            "description",
            "status",
            "default_model_role_id",
            "root_idea_cluster_id",
            "roadmap_id",
        }
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_project(project_id)

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        params: List = list(updates.values())
        params.append(datetime.utcnow().isoformat())
        params.append(project_id)

        with db_session() as conn:
            conn.execute(
                f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?",
                params,
            )
            conn.commit()
            return self.get_project(project_id)

    def delete(self, project_id: str) -> bool:
        with db_session() as conn:
            res = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return res.rowcount > 0

    def _row_to_model(self, row: sqlite3.Row) -> ArgosProject:
        return ArgosProject(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            description=row["description"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            default_model_role_id=row["default_model_role_id"],
            root_idea_cluster_id=row["root_idea_cluster_id"],
            roadmap_id=row["roadmap_id"],
        )


def get_project_repo() -> ProjectRepository:
    return ProjectRepository()

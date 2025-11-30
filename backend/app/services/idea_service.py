from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import (
    ContextItem,
    ContextItemType,
    IdeaCandidate,
    IdeaCandidateStatus,
    IdeaCluster,
    IdeaTicket,
    IdeaTicketPriority,
    IdeaTicketStatus,
    MissionControlTask,
    MissionControlTaskColumn,
    MissionControlTaskOrigin,
)


class IdeaService:
    """
    Ideas service with database persistence for candidates, clusters, tickets, and tasks.
    """

    def list_candidates(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None,
        type: Optional[str] = None,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM idea_candidates WHERE project_id = ?"
            params = [project_id]

            if status:
                query += " AND status = ?"
                params.append(status)
            if type:
                query += " AND type = ?"
                params.append(type)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit + 1)

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_candidate(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM idea_candidates WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_candidate(self, project_id: str, candidate_data: dict) -> IdeaCandidate:
        candidate_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Use content as a fallback for summary to match API helpers in e2e tests
        candidate = IdeaCandidate(
            id=candidate_id,
            project_id=project_id,
            type=candidate_data.get("type", "feature"),
            title=candidate_data.get("title", candidate_data.get("summary") or candidate_data.get("content", "")),
            summary=candidate_data.get("summary") or candidate_data.get("content", ""),
            status=IdeaCandidateStatus(candidate_data.get("status", "active")),
            confidence=candidate_data.get("confidence", 0.85),
            source_log_ids=candidate_data.get("source_log_ids", []),
            source_channel=candidate_data.get("source_channel"),
            source_user=candidate_data.get("source_user"),
            created_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO idea_candidates
                (id, project_id, source_id, source_doc_id, source_doc_chunk_id,
                 title, original_text, summary, status, confidence, cluster_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.id,
                    candidate.project_id,
                    candidate_data.get("source_id", "default"),
                    candidate_data.get("source_doc_id", ""),
                    candidate_data.get("source_doc_chunk_id", ""),
                    candidate.title,
                    candidate_data.get("content", candidate.summary),
                    candidate.summary,
                    candidate.status.value,
                    candidate.confidence,
                    None,
                    candidate.created_at.isoformat(),
                ),
            )
            conn.commit()

        return candidate

    def update_candidate(self, project_id: str, candidate_id: str, updates: dict) -> IdeaCandidate:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM idea_candidates WHERE id = ? AND project_id = ?", (candidate_id, project_id)
            ).fetchone()
            if not row:
                raise ValueError("Idea candidate not found")

            update_fields = []
            params = []

            if "status" in updates:
                update_fields.append("status = ?")
                params.append(updates["status"])
            if "title" in updates:
                update_fields.append("title = ?")
                params.append(updates["title"])
            if "summary" in updates:
                update_fields.append("summary = ?")
                params.append(updates["summary"])

            if update_fields:
                params.extend([candidate_id, project_id])
                query = f"UPDATE idea_candidates SET {', '.join(update_fields)} WHERE id = ? AND project_id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute(
                "SELECT * FROM idea_candidates WHERE id = ? AND project_id = ?", (candidate_id, project_id)
            ).fetchone()
            return self._row_to_candidate(row)

    def list_clusters(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM idea_clusters WHERE project_id = ? ORDER BY created_at DESC LIMIT ?"
            params = [project_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_cluster(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM idea_clusters WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_cluster(self, project_id: str, cluster_data: dict) -> IdeaCluster:
        cluster_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        cluster = IdeaCluster(
            id=cluster_id,
            project_id=project_id,
            label=cluster_data["label"],
            description=cluster_data.get("description"),
            color=cluster_data.get("color"),
            idea_ids=cluster_data.get("idea_ids", []),
            priority=cluster_data.get("priority"),
            created_at=now,
            updated_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO idea_clusters
                (id, project_id, name, summary, idea_ids_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster.id,
                    cluster.project_id,
                    cluster.label,
                    cluster.description or "",
                    json.dumps(cluster.idea_ids),
                    cluster.created_at.isoformat(),
                    cluster.updated_at.isoformat(),
                ),
            )
            conn.commit()

        return cluster

    def list_tickets(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM idea_tickets WHERE project_id = ?"
            params = [project_id]

            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit + 1)

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_ticket(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM idea_tickets WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_ticket(self, project_id: str, ticket_data: dict) -> IdeaTicket:
        ticket_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        ticket = IdeaTicket(
            id=ticket_id,
            project_id=project_id,
            idea_id=ticket_data.get("idea_id"),
            title=ticket_data["title"],
            description=ticket_data.get("description"),
            status=IdeaTicketStatus(ticket_data.get("status", "active")),
            priority=IdeaTicketPriority(ticket_data.get("priority", "medium")),
            origin_story=ticket_data.get("origin_story"),
            category=ticket_data.get("category"),
            implied_task_summaries=ticket_data.get("implied_task_summaries", []),
            repo_hints=ticket_data.get("repo_hints", []),
            source_quotes=ticket_data.get("source_quotes"),
            source_channel=ticket_data.get("source_channel"),
            confidence=ticket_data.get("confidence"),
            created_at=now,
            updated_at=now,
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO idea_tickets
                (id, project_id, cluster_id, title, description, status, priority,
                 created_at, updated_at, origin_idea_ids_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.id,
                    ticket.project_id,
                    ticket.idea_id,  # Using idea_id as cluster_id for now
                    ticket.title,
                    ticket.description,
                    ticket.status.value,
                    ticket.priority.value,
                    ticket.created_at.isoformat(),
                    ticket.updated_at.isoformat(),
                    json.dumps([ticket.idea_id] if ticket.idea_id else []),
                ),
            )
            conn.commit()

        return ticket

    def list_tasks(
        self,
        project_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        column: Optional[str] = None,
        origin: Optional[str] = None,
    ) -> PaginatedResponse:
        # Tasks are stored as idea_tickets with specific metadata
        with db_session() as conn:
            query = "SELECT * FROM idea_tickets WHERE project_id = ?"
            params = [project_id]

            if column:
                # Map column to status
                status_map = {
                    "backlog": "active",
                    "todo": "active",
                    "in_progress": "active",
                    "done": "complete",
                }
                if column in status_map:
                    query += " AND status = ?"
                    params.append(status_map[column])

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit + 1)

            rows = conn.execute(query, params).fetchall()

            items = [self._ticket_row_to_task(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM idea_tickets WHERE project_id = ?", (project_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_task(self, project_id: str, task_data: dict) -> MissionControlTask:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Extract context from task_data
        context_items = []
        if task_data.get("context"):
            for ctx in task_data["context"]:
                context_items.append(
                    ContextItem(
                        id=str(uuid.uuid4()),
                        name=ctx.get("name", ""),
                        type=ContextItemType(ctx.get("type", "other")),
                        tokens=0,
                    )
                )

        task = MissionControlTask(
            id=task_id,
            project_id=project_id,
            title=task_data["title"],
            origin=MissionControlTaskOrigin(task_data.get("origin", "repo")),
            confidence=task_data.get("confidence", 0.85),
            column=MissionControlTaskColumn(task_data.get("column", "backlog")),
            context=context_items,
            priority=task_data.get("priority"),
            idea_id=task_data.get("idea_id"),
            ticket_id=task_data.get("ticket_id"),
            created_at=now,
            updated_at=now,
        )

        # Store as ticket
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO idea_tickets
                (id, project_id, title, description, status, priority, created_at, updated_at, origin_idea_ids_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.project_id,
                    task.title,
                    json.dumps(
                        {
                            "origin": task.origin.value,
                            "confidence": task.confidence,
                            "column": task.column.value,
                        }
                    ),
                    "active",
                    task.priority or "medium",
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    json.dumps([task.idea_id] if task.idea_id else []),
                ),
            )
            conn.commit()

        return task

    def update_task(self, project_id: str, task_id: str, updates: dict) -> MissionControlTask:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM idea_tickets WHERE id = ? AND project_id = ?", (task_id, project_id)
            ).fetchone()
            if not row:
                raise ValueError("Mission control task not found")

            update_fields = []
            params = []

            if "title" in updates:
                update_fields.append("title = ?")
                params.append(updates["title"])
            if "column" in updates:
                # Map column to status
                status_map = {
                    "backlog": "active",
                    "todo": "active",
                    "in_progress": "active",
                    "done": "complete",
                }
                if updates["column"] in status_map:
                    update_fields.append("status = ?")
                    params.append(status_map[updates["column"]])
                # Also update description JSON blob to preserve column information
                # (Tasks are stored as idea_tickets with description.json metadata)
                update_fields.append("description = ?")
                # build new description JSON based on existing data
                old_desc = row.get("description") or "{}"
                try:
                    desc_data = json.loads(old_desc)
                except Exception:
                    desc_data = {}
                desc_data["column"] = updates["column"]
                params.append(json.dumps(desc_data))
            if "priority" in updates:
                update_fields.append("priority = ?")
                params.append(updates["priority"])

            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
                params.extend([task_id, project_id])
                query = f"UPDATE idea_tickets SET {', '.join(update_fields)} WHERE id = ? AND project_id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute(
                "SELECT * FROM idea_tickets WHERE id = ? AND project_id = ?", (task_id, project_id)
            ).fetchone()
            return self._ticket_row_to_task(row)

    def _row_to_candidate(self, row) -> IdeaCandidate:
        return IdeaCandidate(
            id=row["id"],
            project_id=row["project_id"],
            type="feature",  # Default
            title=row.get("title", ""),
            summary=row.get("summary", row.get("original_text", "")),
            status=IdeaCandidateStatus(row.get("status", "active")),
            confidence=row.get("confidence", 0.85),
            source_log_ids=[],
            source_channel=None,
            source_user=None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_cluster(self, row) -> IdeaCluster:
        idea_ids = []
        if row.get("idea_ids_json"):
            try:
                idea_ids = json.loads(row["idea_ids_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return IdeaCluster(
            id=row["id"],
            project_id=row["project_id"],
            label=row.get("name", ""),
            description=row.get("summary"),
            color=None,
            idea_ids=idea_ids,
            priority=None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_ticket(self, row) -> IdeaTicket:
        if row.get("origin_idea_ids_json"):
            try:
                _ = json.loads(row["origin_idea_ids_json"])  # Parse to validate, but don't store
            except (json.JSONDecodeError, ValueError):
                pass

        return IdeaTicket(
            id=row["id"],
            project_id=row["project_id"],
            idea_id=row.get("cluster_id"),
            title=row["title"],
            description=row.get("description"),
            status=IdeaTicketStatus(row["status"]),
            priority=IdeaTicketPriority(row["priority"]),
            origin_story=None,
            category=None,
            implied_task_summaries=[],
            repo_hints=[],
            source_quotes=None,
            source_channel=None,
            confidence=None,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _ticket_row_to_task(self, row) -> MissionControlTask:
        description_data = {}
        if row.get("description"):
            try:
                description_data = json.loads(row["description"])
            except (json.JSONDecodeError, ValueError):
                pass

        return MissionControlTask(
            id=row["id"],
            project_id=row["project_id"],
            title=row["title"],
            origin=MissionControlTaskOrigin(description_data.get("origin", "repo")),
            confidence=description_data.get("confidence", 0.85),
            column=MissionControlTaskColumn(description_data.get("column", "backlog")),
            context=[],
            priority=row.get("priority"),
            idea_id=None,
            ticket_id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


idea_service = IdeaService()

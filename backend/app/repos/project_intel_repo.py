from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.db import db_session
from app.domain.project_intel import (
    IdeaCandidate,
    IdeaCluster,
    IdeaTicket,
    IdeaTicketPriority,
    IdeaTicketStatus,
)

logger = logging.getLogger(__name__)


# ---- candidates ----


def save_candidates(candidates: List[IdeaCandidate]) -> None:
    """
    Upsert a batch of idea candidates.
    """
    with db_session() as conn:
        for c in candidates:
            conn.execute(
                """
                INSERT OR REPLACE INTO idea_candidates
                (id, project_id, source_id, source_doc_id, source_doc_chunk_id,
                 title, original_text, summary, status, confidence, embedding_json, cluster_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.id,
                    c.project_id,
                    c.source_id,
                    c.source_doc_id,
                    c.source_doc_chunk_id,
                    c.title,
                    c.original_text,
                    c.summary,
                    c.status,
                    c.confidence,
                    json.dumps(c.embedding),
                    c.cluster_id,
                    c.created_at.isoformat(),
                ),  # noqa: E501
            )
        conn.commit()
    logger.info(
        "project_intel.save_candidates",
        extra={"count": len(candidates)},
    )


def list_candidates(project_id: Optional[str] = None) -> List[IdeaCandidate]:
    """
    Optionally filter candidates by project_id.
    """
    with db_session() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM idea_candidates WHERE project_id = ?", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM idea_candidates").fetchall()

        candidates = []
        for row in rows:
            candidates.append(
                IdeaCandidate(
                    id=row["id"],
                    project_id=row["project_id"],
                    source_id=row["source_id"],
                    source_doc_id=row["source_doc_id"],
                    source_doc_chunk_id=row["source_doc_chunk_id"],
                    original_text=row["original_text"],
                    summary=row["summary"],
                    title=row.get("title", ""),
                    status=row.get("status", "active"),
                    confidence=row.get("confidence", 0.85),
                    embedding=json.loads(row["embedding_json"] or "null"),
                    cluster_id=row["cluster_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
    return sorted(candidates, key=lambda c: c.id)


def get_candidate(candidate_id: str) -> Optional[IdeaCandidate]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM idea_candidates WHERE id = ?", (candidate_id,)).fetchone()
        if row:
            return IdeaCandidate(
                id=row["id"],
                project_id=row["project_id"],
                source_id=row["source_id"],
                source_doc_id=row["source_doc_id"],
                source_doc_chunk_id=row["source_doc_chunk_id"],
                original_text=row["original_text"],
                summary=row["summary"],
                embedding=json.loads(row["embedding_json"] or "null"),
                cluster_id=row["cluster_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
    return None


# ---- clusters ----


def save_clusters(clusters: List[IdeaCluster]) -> None:
    with db_session() as conn:
        for cluster in clusters:
            conn.execute(
                """
                INSERT OR REPLACE INTO idea_clusters
                (id, project_id, name, summary, idea_ids_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cluster.id,
                    cluster.project_id,
                    cluster.name,
                    cluster.summary,
                    json.dumps(cluster.idea_ids),
                    cluster.created_at.isoformat(),
                    cluster.updated_at.isoformat(),
                ),
            )
        conn.commit()
    logger.info(
        "project_intel.save_clusters",
        extra={"count": len(clusters)},
    )


def list_clusters(project_id: Optional[str] = None) -> List[IdeaCluster]:
    with db_session() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM idea_clusters WHERE project_id = ?", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM idea_clusters").fetchall()

        clusters = []
        for row in rows:
            clusters.append(
                IdeaCluster(
                    id=row["id"],
                    project_id=row["project_id"],
                    name=row["name"],
                    summary=row["summary"],
                    idea_ids=json.loads(row["idea_ids_json"] or "[]"),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )
    # Sort by name for determinism
    return sorted(clusters, key=lambda cl: cl.name)


# ---- tickets ----


def save_tickets(tickets: List[IdeaTicket]) -> None:
    for t in tickets:
        save_ticket(t)
    logger.info(
        "project_intel.save_tickets",
        extra={"count": len(tickets)},
    )


def save_ticket(ticket: IdeaTicket) -> None:
    with db_session() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO idea_tickets
            (id, project_id, cluster_id, title, description, status, priority,
             created_at, updated_at, origin_idea_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket.id,
                ticket.project_id,
                ticket.cluster_id,
                ticket.title,
                ticket.description,
                ticket.status,
                ticket.priority,
                ticket.created_at.isoformat(),
                ticket.updated_at.isoformat(),
                json.dumps(ticket.origin_idea_ids),
            ),
        )
        conn.commit()


def list_tickets(project_id: Optional[str] = None) -> List[IdeaTicket]:
    with db_session() as conn:
        if project_id:
            rows = conn.execute("SELECT * FROM idea_tickets WHERE project_id = ?", (project_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM idea_tickets").fetchall()

        tickets = []
        for row in rows:
            tickets.append(
                IdeaTicket(
                    id=row["id"],
                    project_id=row["project_id"],
                    cluster_id=row["cluster_id"],
                    title=row["title"],
                    description=row["description"],
                    status=row["status"],
                    priority=row["priority"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    origin_idea_ids=json.loads(row["origin_idea_ids_json"] or "[]"),
                )
            )
        # Sort as before
        status_order = {
            "candidate": 0,
            "triaged": 1,
            "planned": 2,
            "in_progress": 3,
            "done": 4,
        }

        priority_order = {"high": 0, "medium": 1, "low": 2}

        def _sort_key(t: IdeaTicket):
            return (
                status_order.get(t.status, 99),
                priority_order.get(t.priority, 99),
                t.created_at,
                t.id,
            )

        return sorted(tickets, key=_sort_key)


def get_ticket(ticket_id: str) -> Optional[IdeaTicket]:
    with db_session() as conn:
        row = conn.execute("SELECT * FROM idea_tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row:
            return IdeaTicket(
                id=row["id"],
                project_id=row["project_id"],
                cluster_id=row["cluster_id"],
                title=row["title"],
                description=row["description"],
                status=row["status"],
                priority=row["priority"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                origin_idea_ids=json.loads(row["origin_idea_ids_json"] or "[]"),
            )
    return None


def update_ticket_status(
    ticket_id: str,
    status: IdeaTicketStatus,
    priority: Optional[IdeaTicketPriority] = None,
) -> Optional[IdeaTicket]:
    ticket = get_ticket(ticket_id)
    if ticket is None:
        return None

    ticket.status = status
    if priority is not None:
        ticket.priority = priority

    ticket.updated_at = datetime.now(timezone.utc)

    save_ticket(ticket)
    logger.info(
        "project_intel.update_ticket_status",
        extra={"ticket_id": ticket_id, "status": status, "priority": priority},
    )
    return ticket

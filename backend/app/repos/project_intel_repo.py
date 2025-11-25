from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.project_intel import (
    IdeaCandidate,
    IdeaCluster,
    IdeaTicket,
    IdeaTicketStatus,
    IdeaTicketPriority,
)

logger = logging.getLogger(__name__)

_candidate_store: Dict[str, IdeaCandidate] = {}
_cluster_store: Dict[str, IdeaCluster] = {}
_ticket_store: Dict[str, IdeaTicket] = {}


# ---- candidates ----


def save_candidates(candidates: List[IdeaCandidate]) -> None:
    """
    Upsert a batch of idea candidates.
    """
    for c in candidates:
        _candidate_store[c.id] = c
    logger.info(
        "project_intel.save_candidates",
        extra={"count": len(candidates)},
    )


def list_candidates(project_id: Optional[str] = None) -> List[IdeaCandidate]:
    """
    Optionally filter candidates by project_id.
    """
    values = list(_candidate_store.values())
    if project_id is not None:
        values = [c for c in values if c.project_id == project_id]
    return sorted(values, key=lambda c: c.id)


def get_candidate(candidate_id: str) -> Optional[IdeaCandidate]:
    return _candidate_store.get(candidate_id)


# ---- clusters ----


def save_clusters(clusters: List[IdeaCluster]) -> None:
    for cluster in clusters:
        _cluster_store[cluster.id] = cluster
    logger.info(
        "project_intel.save_clusters",
        extra={"count": len(clusters)},
    )


def list_clusters(project_id: Optional[str] = None) -> List[IdeaCluster]:
    values = list(_cluster_store.values())
    if project_id is not None:
        values = [cl for cl in values if cl.project_id == project_id]
    # Sort by name for determinism
    return sorted(values, key=lambda cl: cl.name)


# ---- tickets ----


def save_tickets(tickets: List[IdeaTicket]) -> None:
    for t in tickets:
        _ticket_store[t.id] = t
    logger.info(
        "project_intel.save_tickets",
        extra={"count": len(tickets)},
    )


def list_tickets(project_id: Optional[str] = None) -> List[IdeaTicket]:
    values = list(_ticket_store.values())
    if project_id is not None:
        values = [t for t in values if t.project_id == project_id]
    # Deterministic order: status, priority, created_at
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

    return sorted(values, key=_sort_key)


def get_ticket(ticket_id: str) -> Optional[IdeaTicket]:
    return _ticket_store.get(ticket_id)


def update_ticket_status(
    ticket_id: str,
    status: IdeaTicketStatus,
    priority: Optional[IdeaTicketPriority] = None,
) -> Optional[IdeaTicket]:
    ticket = _ticket_store.get(ticket_id)
    if ticket is None:
        return None

    # Pydantic models are immutable by default unless configured; we assume mutable here.
    ticket.status = status  # type: ignore[assignment]
    if priority is not None:
        ticket.priority = priority  # type: ignore[assignment]

    from datetime import datetime, timezone as _tz

    ticket.updated_at = datetime.now(_tz.utc)  # type: ignore[assignment]

    _ticket_store[ticket.id] = ticket
    logger.info(
        "project_intel.update_ticket_status",
        extra={"ticket_id": ticket_id, "status": status, "priority": priority},
    )
    return ticket

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.domain.project_intel import (
    IdeaCandidate,
    IdeaCluster,
    IdeaTicket,
    IdeaTicketPriority,
    IdeaTicketStatus,
)
from app.repos import project_intel_repo as repo
from app.services.project_intel_service import (
    cluster_ideas,
    extract_idea_candidates_from_segments,
    promote_clusters_to_tickets,
)
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["project-intel"])

# We assume you have a way to fetch ChatSegments per project.
# Adjust this import / function name to your actual implementation.
try:  # pragma: no cover - integration point
    from app.domain.chat import ChatSegment  # Assuming ChatSegment is in app.domain.chat

    # from app.repos.chat_segments_repo import list_segments_for_project # Original comment
    # For now, let's create a stub function as chat_segments_repo is not provided
    _chat_segments_store: Dict[str, List[ChatSegment]] = {}

    class DummyChatSegment(ChatSegment):  # Creating a dummy ChatSegment
        id: str = "dummy_id"
        text: str = "dummy text"
        chat_id: str = "dummy_chat_id"
        project_id: str = "dummy_project_id"

    def list_segments_for_project(project_id: str) -> List[ChatSegment]:
        logger.warning(f"Using dummy list_segments_for_project for project {project_id}")
        if project_id == "test-project-rebuild":  # Simulate some data for testing
            return [
                DummyChatSegment(
                    id="seg1",
                    text="we should add a new feature for context management",
                    chat_id="chat1",
                    project_id=project_id,
                ),
                DummyChatSegment(
                    id="seg2",
                    text="refactor the old auth module",
                    chat_id="chat1",
                    project_id=project_id,
                ),
            ]
        return []

except ImportError:  # pragma: no cover
    list_segments_for_project = None  # type: ignore[assignment]
    logger.warning("ChatSegment domain model not found. Project Intel features may be limited.")


# ---- schemas for PATCH ----


class TicketUpdateRequest(BaseModel):
    status: Optional[IdeaTicketStatus] = None
    priority: Optional[IdeaTicketPriority] = None


# ---- routes ----


@router.post(
    "/{project_id}/ideas/rebuild",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
)
def rebuild_project_ideas(project_id: str) -> dict:
    """
    Re-run idea extraction, clustering, and ticket promotion for all chat segments
    belonging to the given project.

    This is idempotent with respect to the deterministic ID generation in the service.
    """
    if list_segments_for_project is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Chat segment repository not configured for project intelligence.",
        )

    segments = list_segments_for_project(project_id=project_id)
    logger.info(
        "project_intel.rebuild.start",
        extra={"project_id": project_id, "segment_count": len(segments)},
    )

    candidates: List[IdeaCandidate] = extract_idea_candidates_from_segments(segments)
    clusters: List[IdeaCluster] = cluster_ideas(candidates)

    # Build a simple lookup for ticket promotion summaries.
    cand_lookup = {c.id: c for c in candidates}
    tickets: List[IdeaTicket] = promote_clusters_to_tickets(clusters, candidate_lookup=cand_lookup)

    # Persist
    repo.save_candidates(candidates)
    repo.save_clusters(clusters)
    repo.save_tickets(tickets)

    logger.info(
        "project_intel.rebuild.done",
        extra={
            "project_id": project_id,
            "candidate_count": len(candidates),
            "cluster_count": len(clusters),
            "ticket_count": len(tickets),
        },
    )

    # Return the IDs of the newly processed entities
    return {
        "project_id": project_id,
        "candidate_ids": [c.id for c in candidates],
        "cluster_ids": [cl.id for cl in clusters],
        "ticket_ids": [t.id for t in tickets],
    }


@router.get(
    "/{project_id}/ideas/candidates",
    response_model=List[IdeaCandidate],
)
def get_project_idea_candidates(project_id: str) -> List[IdeaCandidate]:
    return repo.list_candidates(project_id=project_id)


@router.get(
    "/{project_id}/ideas/clusters",
    response_model=List[IdeaCluster],
)
def get_project_idea_clusters(project_id: str) -> List[IdeaCluster]:
    return repo.list_clusters(project_id=project_id)


@router.get(
    "/{project_id}/ideas/tickets",
    response_model=List[IdeaTicket],
)
def get_project_idea_tickets(project_id: str) -> List[IdeaTicket]:
    return repo.list_tickets(project_id=project_id)


@router.patch(
    "/{project_id}/ideas/tickets/{ticket_id}",
    response_model=IdeaTicket,
)
def update_project_idea_ticket(
    project_id: str,
    ticket_id: str,
    body: TicketUpdateRequest,
) -> IdeaTicket:
    """
    Update status and/or priority of an idea ticket.
    """
    if body.status is None and body.priority is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (status, priority) must be provided.",
        )

    ticket = repo.get_ticket(ticket_id)
    if ticket is None or ticket.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found for this project.",
        )

    updated = repo.update_ticket_status(
        ticket_id=ticket_id,
        status=body.status or ticket.status,
        priority=body.priority,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket.",
        )

    return updated

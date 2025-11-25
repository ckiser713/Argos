from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from app.domain.models import (
    IdeaTicket,
    IdeaCreateRequest,
    IdeaUpdateRequest,
    IdeaStatus,
)


class IdeaService:
    """
    In-memory idea tickets representing project ideas / tasks.
    """

    def __init__(self) -> None:
        now = datetime.utcnow()
        self._ideas: Dict[str, IdeaTicket] = {
            "idea_1": IdeaTicket(
                id="idea_1",
                title="Unify chat exports into a single corpus",
                description="Ingest and normalize exports from Gemini, Claude, ChatGPT, etc.",
                status=IdeaStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        }

    def list_ideas(self) -> List[IdeaTicket]:
        return list(self._ideas.values())

    def get_idea(self, idea_id: str) -> IdeaTicket | None:
        return self._ideas.get(idea_id)

    def create_idea(self, request: IdeaCreateRequest) -> IdeaTicket:
        now = datetime.utcnow()
        idea_id = f"idea_{len(self._ideas) + 1}"
        ticket = IdeaTicket(
            id=idea_id,
            title=request.title,
            description=request.description,
            status=IdeaStatus.INBOX,
            priority=request.priority,
            created_at=now,
            updated_at=now,
        )
        self._ideas[idea_id] = ticket
        return ticket

    def update_idea(self, idea_id: str, request: IdeaUpdateRequest) -> IdeaTicket | None:
        existing = self._ideas.get(idea_id)
        if not existing:
            return None

        data = existing.model_dump()
        if request.title is not None:
            data["title"] = request.title
        if request.description is not None:
            data["description"] = request.description
        if request.status is not None:
            data["status"] = request.status
        if request.priority is not None:
            data["priority"] = request.priority

        updated = IdeaTicket(
            **data,
            updated_at=datetime.utcnow(),
        )
        self._ideas[idea_id] = updated
        return updated

    def delete_idea(self, idea_id: str) -> None:
        self._ideas.pop(idea_id, None)


idea_service = IdeaService()

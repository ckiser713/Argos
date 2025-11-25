from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

IdeaLabel = str
EmbeddingVector = List[float]

IdeaTicketStatus = Literal["candidate", "triaged", "planned", "in_progress", "done"]
IdeaTicketPriority = Literal["low", "medium", "high"]


class IdeaCandidate(BaseModel):
    """
    A raw idea extracted from chat segments.
    This is still close to the original language, but normalized enough to be clusterable.
    """

    id: str
    segment_id: str
    project_id: Optional[str] = None

    title: str
    summary: str

    confidence: float = Field(ge=0.0, le=1.0)
    labels: List[IdeaLabel] = Field(default_factory=list)

    # Which chats did this idea emerge from (for traceability / drill-down)?
    source_chat_ids: List[str] = Field(default_factory=list)


class IdeaCluster(BaseModel):
    """
    A semantic grouping of related IdeaCandidates.
    """

    id: str
    project_id: Optional[str] = None

    name: str
    idea_ids: List[str] = Field(default_factory=list)

    # Optional embedding for the cluster centroid (e.g., stored in Qdrant or in-memory)
    centroid_embedding: Optional[EmbeddingVector] = None


class IdeaTicket(BaseModel):
    """
    A promotable ticket derived from one or more IdeaCandidates (often from a cluster).
    This is what eventually feeds into the Dynamic Project Roadmap / Mission Control.
    """

    id: str
    project_id: Optional[str] = None
    cluster_id: Optional[str] = None

    title: str
    description: str

    status: IdeaTicketStatus = "candidate"
    priority: IdeaTicketPriority = "medium"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    origin_idea_ids: List[str] = Field(default_factory=list)

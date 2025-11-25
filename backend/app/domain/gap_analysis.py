from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

GapStatus = Literal["unmapped", "partially_implemented", "implemented", "unknown"]


class GapSuggestion(BaseModel):
    """
    A single suggestion describing how a specific idea ticket maps to the codebase.
    """

    id: str
    project_id: str
    ticket_id: str
    status: GapStatus
    related_files: List[str] = Field(default_factory=list)
    notes: str
    confidence: float = Field(ge=0.0, le=1.0)

    class Config:
        extra = "ignore"


class GapReport(BaseModel):
    """
    Aggregated gap analysis for a given project at a point in time.
    """

    project_id: str
    generated_at: datetime
    suggestions: List[GapSuggestion] = Field(default_factory=list)

    class Config:
        extra = "ignore"

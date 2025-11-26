from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ChatSegment(BaseModel):
    """
    A segment of chat conversation that can be analyzed for idea extraction.
    
    Chat segments represent individual messages or coherent blocks of conversation
    that may contain actionable ideas, feature requests, or technical discussions.
    """

    id: str = Field(..., description="Unique identifier for the chat segment")
    text: str = Field(..., description="The text content of the chat segment")
    chat_id: str = Field(..., description="Identifier of the chat/conversation this segment belongs to")
    project_id: str = Field(..., description="Identifier of the project this segment is associated with")
    
    # Optional metadata fields
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when this segment was created or sent"
    )
    author: Optional[str] = Field(
        default=None,
        description="Author or sender of this chat segment"
    )
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Additional metadata about the chat segment"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


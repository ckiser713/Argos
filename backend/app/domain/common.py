from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class PaginatedResponse(BaseModel):
    items: list
    next_cursor: Optional[str] = None
    total: Optional[int] = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

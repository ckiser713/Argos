from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.db import db_session
from app.domain.models import (
    AddContextItemsRequest,
    AddContextItemsResponse,
    ContextBudget,
    ContextItem,
    ContextItemType,
)


class ContextService:
    """
    Database-backed context items with budget management.
    """

    DEFAULT_MAX_TOKENS = 100000  # Default project token limit

    def list_items(self, project_id: Optional[str] = None) -> List[ContextItem]:
        with db_session() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM context_items WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM context_items ORDER BY created_at DESC").fetchall()
            return [self._row_to_item(row) for row in rows]

    def get_budget(self, project_id: str) -> ContextBudget:
        items = self.list_items(project_id)
        used_tokens = sum(item.tokens for item in items)
        total_tokens = self.DEFAULT_MAX_TOKENS
        available_tokens = total_tokens - used_tokens

        return ContextBudget(
            project_id=project_id,
            total_tokens=total_tokens,
            used_tokens=used_tokens,
            available_tokens=available_tokens,
            items=items,
        )

    def add_items(self, project_id: str, request: AddContextItemsRequest) -> AddContextItemsResponse:
        # Calculate current budget
        current_budget = self.get_budget(project_id)
        new_tokens = sum(item.tokens for item in request.items)

        if current_budget.used_tokens + new_tokens > current_budget.total_tokens:
            raise ValueError(
                f"Budget exceeded. Would use {current_budget.used_tokens + new_tokens} tokens, "
                f"limit is {current_budget.total_tokens}"
            )

        # Add items atomically
        now = datetime.now(timezone.utc)
        created_items = []
        with db_session() as conn:
            for item in request.items:
                item_id = item.id if item.id else str(uuid.uuid4())
                created_item = ContextItem(
                    id=item_id,
                    name=item.name,
                    type=item.type,
                    tokens=item.tokens,
                    pinned=item.pinned if hasattr(item, "pinned") else False,
                    canonical_document_id=item.canonical_document_id
                    if hasattr(item, "canonical_document_id")
                    else None,
                    created_at=now,
                )
                conn.execute(
                    """
                    INSERT INTO context_items
                    (id, project_id, name, type, tokens, pinned, canonical_document_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_item.id,
                        project_id,
                        created_item.name,
                        created_item.type.value,
                        created_item.tokens,
                        1 if created_item.pinned else 0,
                        created_item.canonical_document_id,
                        created_item.created_at.isoformat(),
                    ),
                )
                created_items.append(created_item)
            conn.commit()

        updated_budget = self.get_budget(project_id)
        return AddContextItemsResponse(items=created_items, budget=updated_budget)

    def update_item(
        self,
        project_id: str,
        item_id: str,
        *,
        pinned: Optional[bool] = None,
        tokens: Optional[int] = None,
    ) -> ContextItem:
        with db_session() as conn:
            # Check item exists and belongs to project
            row = conn.execute(
                "SELECT * FROM context_items WHERE id = ? AND project_id = ?", (item_id, project_id)
            ).fetchone()
            if not row:
                raise ValueError("Context item not found")

            updates = []
            params = []

            if pinned is not None:
                updates.append("pinned = ?")
                params.append(1 if pinned else 0)
            if tokens is not None:
                updates.append("tokens = ?")
                params.append(tokens)

            if updates:
                params.extend([item_id, project_id])
                query = f"UPDATE context_items SET {', '.join(updates)} WHERE id = ? AND project_id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute(
                "SELECT * FROM context_items WHERE id = ? AND project_id = ?", (item_id, project_id)
            ).fetchone()
            return self._row_to_item(row)

    def remove_item(self, project_id: str, item_id: str) -> ContextBudget:
        with db_session() as conn:
            # Check item exists and belongs to project
            row = conn.execute(
                "SELECT * FROM context_items WHERE id = ? AND project_id = ?", (item_id, project_id)
            ).fetchone()
            if not row:
                raise ValueError("Context item not found")

            conn.execute("DELETE FROM context_items WHERE id = ? AND project_id = ?", (item_id, project_id))
            conn.commit()

        return self.get_budget(project_id)

    def _row_to_item(self, row) -> ContextItem:
        return ContextItem(
            id=row["id"],
            name=row["name"],
            type=ContextItemType(row["type"]),
            tokens=row["tokens"],
            pinned=bool(row["pinned"] if "pinned" in row.keys() else 0),
            canonical_document_id=row["canonical_document_id"] if "canonical_document_id" in row.keys() else None,
            created_at=datetime.fromisoformat(row["created_at"]) if "created_at" in row.keys() and row["created_at"] else None,
        )


context_service = ContextService()

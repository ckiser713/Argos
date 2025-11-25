from __future__ import annotations

from typing import Dict, List

from app.domain.models import ContextItem, ContextItemType


class ContextService:
    """
    In-memory context items.

    This is where you'll later hook into whatever context/index store
    you end up using (e.g., vector DB + metadata store).
    """

    def __init__(self) -> None:
        self._items: Dict[str, ContextItem] = {
            "c1": ContextItem(
                id="c1",
                name="Project_Titan_Specs.pdf",
                type=ContextItemType.PDF,
                tokens=45000,
            ),
            "c2": ContextItem(
                id="c2",
                name="auth_middleware.rs",
                type=ContextItemType.REPO,
                tokens=12500,
            ),
            "c3": ContextItem(
                id="c3",
                name="user_session.ts",
                type=ContextItemType.REPO,
                tokens=8200,
            ),
            "c4": ContextItem(
                id="c4",
                name="DeepResearch_Chat_Log_001",
                type=ContextItemType.CHAT,
                tokens=4100,
            ),
        }

    def list_items(self) -> List[ContextItem]:
        return list(self._items.values())

    def add_item(self, item: ContextItem) -> ContextItem:
        self._items[item.id] = item
        return item

    def remove_item(self, item_id: str) -> None:
        self._items.pop(item_id, None)


context_service = ContextService()

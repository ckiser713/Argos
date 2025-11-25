from typing import List

from fastapi import APIRouter, HTTPException

from app.domain.models import ContextItem
from app.services.context_service import context_service

router = APIRouter()


@router.get("/items", response_model=List[ContextItem], summary="List all context items")
def list_context_items() -> List[ContextItem]:
    return context_service.list_items()


@router.delete(
    "/items/{item_id}",
    status_code=204,
    summary="Remove an item from context",
)
def delete_context_item(item_id: str) -> None:
    existing = [i for i in context_service.list_items() if i.id == item_id]
    if not existing:
        raise HTTPException(status_code=404, detail="Context item not found")
    context_service.remove_item(item_id)

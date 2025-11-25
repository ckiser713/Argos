from __future__ import annotations

from typing import List

from app.domain.models import (
    AddContextItemsRequest,
    AddContextItemsResponse,
    ContextBudget,
    ContextItem,
)
from app.services.context_service import context_service
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/projects/{project_id}/context", response_model=ContextBudget, summary="Get context budget and items")
def get_context(project_id: str) -> ContextBudget:
    return context_service.get_budget(project_id)


@router.post(
    "/projects/{project_id}/context/items", response_model=AddContextItemsResponse, summary="Add context items"
)
def add_context_items(
    project_id: str,
    request: AddContextItemsRequest,
) -> AddContextItemsResponse:
    try:
        return context_service.add_items(project_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/projects/{project_id}/context/items/{context_item_id}", response_model=ContextItem, summary="Update context item"
)
def update_context_item(
    project_id: str,
    context_item_id: str,
    item: dict,  # Accept partial update
) -> ContextItem:
    try:
        pinned = item.get("pinned")
        tokens = item.get("tokens")
        return context_service.update_item(
            project_id,
            context_item_id,
            pinned=pinned,
            tokens=tokens,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/projects/{project_id}/context/items/{context_item_id}",
    response_model=ContextBudget,
    summary="Remove context item",
)
def remove_context_item(
    project_id: str,
    context_item_id: str,
) -> ContextBudget:
    try:
        return context_service.remove_item(project_id, context_item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/projects/{project_id}/context/items", response_model=List[ContextItem], summary="List all context items")
def list_context_items(project_id: str) -> List[ContextItem]:
    return context_service.list_items(project_id=project_id)

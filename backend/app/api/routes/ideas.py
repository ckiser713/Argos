from typing import List

from fastapi import APIRouter, HTTPException, status

from app.domain.models import (
    IdeaTicket,
    IdeaCreateRequest,
    IdeaUpdateRequest,
)
from app.services.idea_service import idea_service

router = APIRouter()


@router.get("/", response_model=List[IdeaTicket], summary="List ideas")
def list_ideas() -> List[IdeaTicket]:
    return idea_service.list_ideas()


@router.post(
    "/",
    response_model=IdeaTicket,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new idea",
)
def create_idea(request: IdeaCreateRequest) -> IdeaTicket:
    return idea_service.create_idea(request)


@router.get("/{idea_id}", response_model=IdeaTicket, summary="Get a single idea")
def get_idea(idea_id: str) -> IdeaTicket:
    idea = idea_service.get_idea(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.patch("/{idea_id}", response_model=IdeaTicket, summary="Update an idea")
def update_idea(idea_id: str, request: IdeaUpdateRequest) -> IdeaTicket:
    idea = idea_service.update_idea(idea_id, request)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.delete("/{idea_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an idea")
def delete_idea(idea_id: str) -> None:
    existing = idea_service.get_idea(idea_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Idea not found")
    idea_service.delete_idea(idea_id)

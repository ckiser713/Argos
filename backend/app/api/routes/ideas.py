from __future__ import annotations

from typing import Optional

from app.domain.common import PaginatedResponse
from app.domain.models import (
    IdeaCandidate,
    IdeaCluster,
    IdeaTicket,
    MissionControlTask,
)
from app.services.idea_service import idea_service
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


# Idea Candidates
@router.get("/projects/{project_id}/ideas/candidates", response_model=PaginatedResponse, summary="List idea candidates")
def list_idea_candidates(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
) -> PaginatedResponse:
    return idea_service.list_candidates(
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        status=status,
        type=type,
    )


@router.post(
    "/projects/{project_id}/ideas/candidates",
    response_model=IdeaCandidate,
    status_code=201,
    summary="Create idea candidate",
)
def create_idea_candidate(
    project_id: str,
    candidate_data: dict,
) -> IdeaCandidate:
    return idea_service.create_candidate(project_id, candidate_data)


@router.patch(
    "/projects/{project_id}/ideas/candidates/{idea_id}", response_model=IdeaCandidate, summary="Update idea candidate"
)
def update_idea_candidate(
    project_id: str,
    idea_id: str,
    updates: dict,
) -> IdeaCandidate:
    try:
        return idea_service.update_candidate(project_id, idea_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Idea Clusters
@router.get("/projects/{project_id}/ideas/clusters", response_model=PaginatedResponse, summary="List idea clusters")
def list_idea_clusters(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    return idea_service.list_clusters(project_id=project_id, cursor=cursor, limit=limit)


@router.post(
    "/projects/{project_id}/ideas/clusters", response_model=IdeaCluster, status_code=201, summary="Create idea cluster"
)
def create_idea_cluster(
    project_id: str,
    cluster_data: dict,
) -> IdeaCluster:
    return idea_service.create_cluster(project_id, cluster_data)


# Idea Tickets
@router.get("/projects/{project_id}/ideas/tickets", response_model=PaginatedResponse, summary="List idea tickets")
def list_idea_tickets(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
) -> PaginatedResponse:
    return idea_service.list_tickets(
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        status=status,
    )


@router.post(
    "/projects/{project_id}/ideas/tickets",
    response_model=IdeaTicket,
    status_code=201,
    summary="Create ticket from idea",
)
def create_idea_ticket(
    project_id: str,
    ticket_data: dict,
) -> IdeaTicket:
    return idea_service.create_ticket(project_id, ticket_data)


# Mission Control Tasks
@router.get("/projects/{project_id}/tasks", response_model=PaginatedResponse, summary="List mission control tasks")
def list_mission_control_tasks(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    column: Optional[str] = Query(default=None),
    origin: Optional[str] = Query(default=None),
) -> PaginatedResponse:
    return idea_service.list_tasks(
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        column=column,
        origin=origin,
    )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=MissionControlTask,
    status_code=201,
    summary="Create mission control task",
)
def create_mission_control_task(
    project_id: str,
    task_data: dict,
) -> MissionControlTask:
    return idea_service.create_task(project_id, task_data)


@router.patch(
    "/projects/{project_id}/tasks/{task_id}", response_model=MissionControlTask, summary="Update mission control task"
)
def update_mission_control_task(
    project_id: str,
    task_id: str,
    updates: dict,
) -> MissionControlTask:
    try:
        return idea_service.update_task(project_id, task_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

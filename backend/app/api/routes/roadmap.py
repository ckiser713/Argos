from __future__ import annotations

from typing import Optional

from app.domain.common import PaginatedResponse
from app.domain.models import (
    RoadmapEdge,
    RoadmapGraph,
    RoadmapNode,
)
from app.services.roadmap_service import roadmap_service
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/projects/{project_id}/roadmap/nodes", response_model=PaginatedResponse, summary="List roadmap nodes")
def list_roadmap_nodes(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    lane_id: Optional[str] = Query(default=None),
) -> PaginatedResponse:
    return roadmap_service.list_nodes(
        project_id=project_id,
        cursor=cursor,
        limit=limit,
        status=status,
        lane_id=lane_id,
    )


@router.post(
    "/projects/{project_id}/roadmap/nodes", response_model=RoadmapNode, status_code=201, summary="Create roadmap node"
)
def create_roadmap_node(
    project_id: str,
    node_data: dict,
) -> RoadmapNode:
    try:
        return roadmap_service.create_node(project_id, node_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/roadmap/nodes/{node_id}", response_model=RoadmapNode, summary="Get roadmap node")
def get_roadmap_node(
    project_id: str,
    node_id: str,
) -> RoadmapNode:
    node = roadmap_service.get_node(project_id, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Roadmap node not found")
    return node


@router.patch(
    "/projects/{project_id}/roadmap/nodes/{node_id}", response_model=RoadmapNode, summary="Update roadmap node"
)
def update_roadmap_node(
    project_id: str,
    node_id: str,
    updates: dict,
) -> RoadmapNode:
    try:
        return roadmap_service.update_node(project_id, node_id, updates)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/projects/{project_id}/roadmap/nodes/{node_id}", status_code=200, summary="Delete roadmap node")
def delete_roadmap_node(
    project_id: str,
    node_id: str,
):
    try:
        roadmap_service.delete_node(project_id, node_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/roadmap/edges", response_model=PaginatedResponse, summary="List roadmap edges")
def list_roadmap_edges(
    project_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    return roadmap_service.list_edges(project_id=project_id, cursor=cursor, limit=limit)


@router.post(
    "/projects/{project_id}/roadmap/edges", response_model=RoadmapEdge, status_code=201, summary="Create roadmap edge"
)
def create_roadmap_edge(
    project_id: str,
    edge_data: dict,
) -> RoadmapEdge:
    try:
        return roadmap_service.create_edge(project_id, edge_data)
    except ValueError as e:
        status_code = 409 if "already exists" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete("/projects/{project_id}/roadmap/edges/{edge_id}", status_code=200, summary="Delete roadmap edge")
def delete_roadmap_edge(
    project_id: str,
    edge_id: str,
):
    roadmap_service.delete_edge(project_id, edge_id)
    return {"success": True}


@router.get("/projects/{project_id}/roadmap", response_model=RoadmapGraph, summary="Get complete roadmap graph")
def get_roadmap_graph(
    project_id: str,
) -> RoadmapGraph:
    return roadmap_service.get_graph(project_id)

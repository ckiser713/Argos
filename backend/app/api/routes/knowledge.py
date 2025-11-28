from __future__ import annotations

from typing import List, Optional

from app.domain.models import (
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeSearchRequest,
)
from app.services.knowledge_service import knowledge_service
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get(
    "/projects/{project_id}/knowledge-graph", response_model=KnowledgeGraph, summary="Get knowledge graph snapshot"
)
def get_knowledge_graph(
    project_id: str,
    view: Optional[str] = Query(default=None),
    focus_node_id: Optional[str] = Query(default=None),
) -> KnowledgeGraph:
    return knowledge_service.get_graph(project_id, view=view, focus_node_id=focus_node_id)


@router.get(
    "/projects/{project_id}/knowledge-graph/nodes/{node_id}",
    response_model=KnowledgeNode,
    summary="Get single knowledge node",
)
def get_knowledge_node(
    project_id: str,
    node_id: str,
) -> KnowledgeNode:
    node = knowledge_service.get_node(project_id, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")
    return node


@router.get(
    "/projects/{project_id}/knowledge-graph/nodes/{node_id}/neighbors",
    response_model=dict,
    summary="Get neighbors for a node",
)
def get_knowledge_node_neighbors(
    project_id: str,
    node_id: str,
) -> dict:
    try:
        return knowledge_service.get_node_neighbors(project_id, node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/projects/{project_id}/knowledge-graph/nodes",
    response_model=KnowledgeNode,
    status_code=201,
    summary="Create knowledge node",
)
def create_knowledge_node(
    project_id: str,
    node_data: dict,
) -> KnowledgeNode:
    try:
        return knowledge_service.create_node(project_id, node_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/projects/{project_id}/knowledge-graph/nodes/{node_id}",
    response_model=KnowledgeNode,
    summary="Update knowledge node",
)
def update_knowledge_node(
    project_id: str,
    node_id: str,
    updates: dict,
) -> KnowledgeNode:
    try:
        return knowledge_service.update_node(project_id, node_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/projects/{project_id}/knowledge-graph/nodes/{node_id}",
    status_code=200,
    summary="Delete knowledge node",
)
def delete_knowledge_node(
    project_id: str,
    node_id: str,
):
    try:
        knowledge_service.delete_node(project_id, node_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/projects/{project_id}/knowledge-graph/edges",
    response_model=KnowledgeEdge,
    status_code=201,
    summary="Create knowledge edge",
)
def create_knowledge_edge(
    project_id: str,
    edge_data: dict,
) -> KnowledgeEdge:
    try:
        return knowledge_service.create_edge(project_id, edge_data)
    except ValueError as e:
        status_code = 409 if "already exists" in str(e).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(e))


@router.delete(
    "/projects/{project_id}/knowledge-graph/edges/{edge_id}", status_code=200, summary="Delete knowledge edge"
)
def delete_knowledge_edge(
    project_id: str,
    edge_id: str,
):
    knowledge_service.delete_edge(project_id, edge_id)
    return {"success": True}


@router.post(
    "/projects/{project_id}/knowledge/search", response_model=List[KnowledgeNode], summary="Search knowledge nodes"
)
def search_knowledge(
    project_id: str,
    request: KnowledgeSearchRequest,
) -> List[KnowledgeNode]:
    return knowledge_service.search(project_id, request)


@router.post(
    "/projects/{project_id}/knowledge/auto-link",
    response_model=List[KnowledgeEdge],
    summary="Automatically link similar knowledge nodes",
)
def auto_link_knowledge_nodes(
    project_id: str,
    request: dict,
) -> List[KnowledgeEdge]:
    """
    Automatically create knowledge edges between nodes with high semantic similarity.
    """
    similarity_threshold = request.get("similarity_threshold", 0.7)
    return knowledge_service.auto_link_documents(project_id, similarity_threshold)


@router.post(
    "/projects/{project_id}/knowledge/link-document-to-repo",
    response_model=KnowledgeEdge,
    summary="Link a document node to a repository node",
)
def link_document_to_repo(
    project_id: str,
    request: dict,
) -> KnowledgeEdge:
    """
    Manually create a link between a document (PDF) and a repository node.
    """
    document_node_id = request["document_node_id"]
    repo_node_id = request["repo_node_id"]
    link_strength = request.get("link_strength")
    
    try:
        return knowledge_service.link_document_to_repo(
            project_id,
            document_node_id,
            repo_node_id,
            link_strength,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

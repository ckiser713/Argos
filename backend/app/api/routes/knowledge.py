from __future__ import annotations

from typing import List, Optional

from app.domain.models import (
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeSearchRequest,
)
from app.services.knowledge_service import knowledge_service
from app.services.rag_service import rag_service
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
    response_model=dict,
    status_code=201,
    summary="Create knowledge edge",
)
def create_knowledge_edge(
    project_id: str,
    edge_data: dict,
) -> dict:
    try:
        edge = knowledge_service.create_edge(project_id, edge_data)
        # Provide compatibility with older clients expecting source_id/target_id
        return {
            "id": edge.id,
            "project_id": edge.project_id,
            "source": edge.source,
            "target": edge.target,
            "source_id": edge.source,
            "target_id": edge.target,
            "type": edge.type,
            "label": edge.label,
            "created_at": edge.created_at,
        }
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
    "/projects/{project_id}/knowledge-graph/search",
    response_model=dict,
    summary="Compatibility: Search knowledge graph (alias)",
)
def search_knowledge_graph(project_id: str, request: KnowledgeSearchRequest) -> dict:
    """Compatibility endpoint used by older tests/clients that reference 'knowledge-graph/search'.
    Returns a dict with 'results' key for backwards compatibility.
    """
    # For compatibility with advanced RAG features (citations, query rewriting),
    # delegate to rag_service.search which returns results and citations.
    try:
        response = rag_service.search(project_id=project_id, query=request.query, limit=request.max_results)
        # If RAG search failed due to missing embeddings or models, fall back to text search
        query_meta = response.get("query_metadata", {}) if isinstance(response, dict) else {}
        if not response.get("results") and query_meta.get("error"):
            results = knowledge_service.search(project_id, request)
            # Transform nodes into compatibility dicts
            transformed = []
            for node in results:
                node_dict = {
                    "id": node.id,
                    "project_id": node.project_id,
                    "title": node.title,
                    "summary": node.summary,
                    "type": node.type,
                    "metadata": node.metadata or {},
                }
                if node_dict["metadata"].get("document_id"):
                    node_dict["document_id"] = node_dict["metadata"].get("document_id")
                if node_dict["metadata"].get("source"):
                    node_dict["source"] = node_dict["metadata"].get("source")
                transformed.append(node_dict)
            return {"results": transformed}
        # Normalize results for backwards compatibility: ensure 'document_id' and 'source' are top-level
        try:
            results = response.get("results", []) if isinstance(response, dict) else []
            # If the RAG service returned a raw list of nodes
            if isinstance(response, list):
                results = response
            normalized = []
            def _to_dict(x):
                if isinstance(x, dict):
                    return x
                if hasattr(x, "model_dump"):
                    try:
                        return x.model_dump()
                    except Exception:
                        pass
                if hasattr(x, "dict"):
                    try:
                        return x.dict()
                    except Exception:
                        pass
                try:
                    return dict(x)
                except Exception:
                    return {"value": str(x)}

            for r in results:
                rr = _to_dict(r)
                meta = rr.get("metadata") if isinstance(rr.get("metadata"), dict) else {}
                # Add top-level fields based on metadata when present
                if not rr.get("document_id") and meta.get("document_id"):
                    rr["document_id"] = meta.get("document_id")
                if not rr.get("source") and meta.get("source"):
                    rr["source"] = meta.get("source")
                # If no content present, try to fallback to summary/title
                if not rr.get("content"):
                    rr["content"] = rr.get("summary") or rr.get("title") or meta.get("content") or ""
                normalized.append(rr)
            if isinstance(response, dict):
                response["results"] = normalized
            else:
                response = {"results": normalized}
        except Exception:
            pass
        return response
    except Exception:
        # Fall back to simple knowledge search if RAG search raised an exception
        results = knowledge_service.search(project_id, request)
        # Transform KnowledgeNode objects into a compatible dict format with
        # 'source' and 'document_id' in top-level keys where available.
        transformed = []
        for node in results:
            node_dict = {
                "id": node.id,
                "project_id": node.project_id,
                "title": node.title,
                "summary": node.summary,
                "type": node.type,
                "metadata": node.metadata or {},
            }
            if node_dict["metadata"].get("document_id"):
                node_dict["document_id"] = node_dict["metadata"].get("document_id")
            if node_dict["metadata"].get("source"):
                node_dict["source"] = node_dict["metadata"].get("source")
            transformed.append(node_dict)
        return {"results": transformed}


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
    "/projects/{project_id}/knowledge-graph/auto-link",
    response_model=dict,
    summary="Compatibility: Automatically link similar knowledge nodes",
)
def auto_link_knowledge_nodes_compat(project_id: str, request: dict) -> List[KnowledgeEdge]:
    """Compatibility alias used by older clients referencing 'knowledge-graph/auto-link'."""
    similarity_threshold = request.get("similarity_threshold", 0.7)
    edges = knowledge_service.auto_link_documents(project_id, similarity_threshold)
    return {"links_created": [e.id for e in edges], "edges": edges, "success": True}


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

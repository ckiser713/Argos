from __future__ import annotations

from typing import Dict, List

from app.domain.models import KnowledgeNode, KnowledgeSearchRequest


class KnowledgeService:
    """
    In-memory knowledge nodes for the knowledge graph view.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, KnowledgeNode] = {
            "n1": KnowledgeNode(
                id="n1",
                title="Vector Databases 101",
                summary="High-level notes on vector DB tradeoffs and architectures.",
                tags=["vector-db", "retrieval"],
                related_ids=["n2"],
            ),
            "n2": KnowledgeNode(
                id="n2",
                title="LangGraph Orchestration Design",
                summary="Notes on how to wire LangGraph with Cortex pipelines.",
                tags=["orchestration", "langgraph"],
                related_ids=["n1"],
            ),
        }

    def list_nodes(self) -> List[KnowledgeNode]:
        return list(self._nodes.values())

    def search(self, request: KnowledgeSearchRequest) -> List[KnowledgeNode]:
        q = request.query.lower()
        results: List[KnowledgeNode] = []
        for node in self._nodes.values():
            haystack = " ".join(
                [node.title or "", node.summary or "", " ".join(node.tags)]
            ).lower()
            if q in haystack:
                results.append(node)
            if len(results) >= request.max_results:
                break
        return results


knowledge_service = KnowledgeService()

"""
Qdrant vector database service for storing and searching embeddings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Service for managing Qdrant vector database operations.
    Handles collections, embeddings, and vector search.
    """

    def __init__(self):
        settings = get_settings()
        qdrant_url = getattr(settings, "qdrant_url", "http://localhost:6333")

        try:
            self.client = QdrantClient(url=qdrant_url)
            # Test connection
            self.client.get_collections()
            logger.info(f"Connected to Qdrant at {qdrant_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}. Vector search will be disabled.")
            self.client = None

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.embedding_size = 384
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self.embedding_model = None
            self.embedding_size = 384

    def _get_collection_name(self, project_id: str, collection_type: str = "knowledge") -> str:
        """Generate collection name for a project."""
        return f"{collection_type}_{project_id}"

    def ensure_collection(self, project_id: str, collection_type: str = "knowledge") -> bool:
        """Ensure a collection exists for a project."""
        if not self.client:
            return False

        collection_name = self._get_collection_name(project_id, collection_type)

        try:
            if not self.client.collection_exists(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=self.embedding_size, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        if not self.embedding_model:
            return None
        try:
            return self.embedding_model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def upsert_knowledge_node(
        self,
        project_id: str,
        node_id: str,
        title: str,
        summary: Optional[str] = None,
        text: Optional[str] = None,
        node_type: Optional[str] = None,
    ) -> bool:
        """Store or update a knowledge node with its embedding."""
        if not self.client or not self.embedding_model:
            return False

        if not self.ensure_collection(project_id, "knowledge"):
            return False

        # Generate embedding from title + summary + text
        text_to_embed = f"{title}"
        if summary:
            text_to_embed += f" {summary}"
        if text:
            text_to_embed += f" {text[:500]}"  # Limit text length

        embedding = self.generate_embedding(text_to_embed)
        if not embedding:
            return False

        collection_name = self._get_collection_name(project_id, "knowledge")

        try:
            point = PointStruct(
                id=node_id,
                vector=embedding,
                payload={
                    "node_id": node_id,
                    "project_id": project_id,
                    "title": title,
                    "summary": summary or "",
                    "type": node_type or "concept",
                },
            )
            self.client.upsert(collection_name=collection_name, points=[point])
            return True
        except Exception as e:
            logger.error(f"Failed to upsert knowledge node: {e}")
            return False

    def delete_knowledge_node(self, project_id: str, node_id: str) -> bool:
        """Delete a knowledge node from Qdrant."""
        if not self.client:
            return False

        collection_name = self._get_collection_name(project_id, "knowledge")

        try:
            self.client.delete(collection_name=collection_name, points_selector=[node_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete knowledge node: {e}")
            return False

    def search_knowledge_nodes(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        node_type: Optional[str] = None,
        use_vector_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search knowledge nodes by similarity."""
        if not self.client or not self.embedding_model:
            return []

        collection_name = self._get_collection_name(project_id, "knowledge")

        if not self.client.collection_exists(collection_name):
            return []

        try:
            results = []

            if use_vector_search:
                # Vector similarity search
                query_embedding = self.generate_embedding(query)
                if query_embedding:
                    # Build filter
                    filter_condition = None
                    if node_type:
                        filter_condition = Filter(must=[FieldCondition(key="type", match=MatchValue(value=node_type))])

                    search_results = self.client.search(
                        collection_name=collection_name,
                        query_vector=query_embedding,
                        limit=limit,
                        query_filter=filter_condition,
                    )

                    results = [
                        {
                            "node_id": r.payload.get("node_id"),
                            "title": r.payload.get("title"),
                            "summary": r.payload.get("summary"),
                            "type": r.payload.get("type"),
                            "score": r.score,
                        }
                        for r in search_results
                    ]
            else:
                # Keyword search (fallback to text search in payload)
                # This is a simple implementation - in production you'd use Qdrant's full-text search
                logger.warning("Keyword-only search not fully implemented, using vector search")
                return self.search_knowledge_nodes(project_id, query, limit, node_type, True)

            return results
        except Exception as e:
            logger.error(f"Failed to search knowledge nodes: {e}")
            return []

    def hybrid_search(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        node_type: Optional[str] = None,
        vector_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and keyword search."""
        # For now, use vector search
        # In production, you'd combine vector search results with keyword search results
        return self.search_knowledge_nodes(
            project_id,
            query,
            limit,
            node_type,
            use_vector_search=True,
        )


# Global instance
qdrant_service = QdrantService()

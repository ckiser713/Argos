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

                    search_func = getattr(self.client, "search", None) or getattr(self.client, "search_points", None)
                    if not search_func:
                        logger.warning("Qdrant client missing search API, skipping vector search")
                        search_results = []
                    else:
                        search_kwargs = {
                            "collection_name": collection_name,
                            "query_vector": query_embedding,
                            "limit": limit,
                        }
                        if filter_condition:
                            search_kwargs["query_filter"] = filter_condition

                        search_results = search_func(**search_kwargs)

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
        """
        Hybrid search combining vector and keyword search.
        Combines results from both search methods and re-ranks them.
        """
        if not self.client or not self.embedding_model:
            return []

        collection_name = self._get_collection_name(project_id, "knowledge")
        if not self.client.collection_exists(collection_name):
            return []

        try:
            # Vector search
            vector_results = []
            if vector_weight > 0:
                query_embedding = self.generate_embedding(query)
                if query_embedding:
                    filter_condition = None
                    if node_type:
                        filter_condition = Filter(must=[FieldCondition(key="type", match=MatchValue(value=node_type))])

                    search_kwargs = {
                        "collection_name": collection_name,
                        "query_vector": query_embedding,
                        "limit": limit * 2,  # Get more results for re-ranking
                    }
                    if filter_condition:
                        search_kwargs["query_filter"] = filter_condition

                    vector_results = self.client.search(**search_kwargs)

            # Keyword search (simple text matching in payload)
            keyword_results = []
            if vector_weight < 1.0:
                # Use scroll to get all points and filter by keyword
                try:
                    scroll_result = self.client.scroll(
                        collection_name=collection_name,
                        limit=1000,  # Adjust based on collection size
                        with_payload=True,
                    )
                    query_lower = query.lower()
                    for point in scroll_result[0]:
                        payload = point.payload
                        title = (payload.get("title") or "").lower()
                        summary = (payload.get("summary") or "").lower()
                        if query_lower in title or query_lower in summary:
                            # Simple scoring: title match = 0.5, summary match = 0.3
                            score = 0.5 if query_lower in title else 0.3
                            keyword_results.append({
                                "node_id": payload.get("node_id"),
                                "title": payload.get("title"),
                                "summary": payload.get("summary"),
                                "type": payload.get("type"),
                                "score": score,
                            })
                except Exception as e:
                    logger.warning(f"Keyword search failed: {e}")

            # Combine and re-rank results
            combined = {}
            
            # Add vector results with weighted scores
            for result in vector_results:
                node_id = result.payload.get("node_id")
                if node_id:
                    combined[node_id] = {
                        "node_id": node_id,
                        "title": result.payload.get("title"),
                        "summary": result.payload.get("summary"),
                        "type": result.payload.get("type"),
                        "score": result.score * vector_weight,
                        "vector_score": result.score,
                        "keyword_score": 0.0,
                    }

            # Add keyword results, combining scores if already present
            for result in keyword_results:
                node_id = result["node_id"]
                keyword_score = result["score"] * (1.0 - vector_weight)
                if node_id in combined:
                    combined[node_id]["score"] += keyword_score
                    combined[node_id]["keyword_score"] = keyword_score
                else:
                    combined[node_id] = {
                        "node_id": node_id,
                        "title": result["title"],
                        "summary": result["summary"],
                        "type": result["type"],
                        "score": keyword_score,
                        "vector_score": 0.0,
                        "keyword_score": keyword_score,
                    }

            # Sort by combined score and return top results
            sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
            return sorted_results[:limit]

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            # Fallback to vector search only
            return self.search_knowledge_nodes(project_id, query, limit, node_type, use_vector_search=True)

    def batch_upsert_knowledge_nodes(
        self,
        project_id: str,
        nodes: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Batch upsert knowledge nodes for efficient bulk ingestion.
        Returns number of successfully upserted nodes.
        """
        if not self.client or not self.embedding_model:
            return 0

        if not self.ensure_collection(project_id, "knowledge"):
            return 0

        collection_name = self._get_collection_name(project_id, "knowledge")
        upserted_count = 0

        try:
            # Process in batches
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                points = []

                for node_data in batch:
                    node_id = node_data.get("node_id")
                    title = node_data.get("title", "")
                    summary = node_data.get("summary", "")
                    text = node_data.get("text", "")
                    node_type = node_data.get("type", "concept")

                    # Generate embedding
                    text_to_embed = title
                    if summary:
                        text_to_embed += f" {summary}"
                    if text:
                        text_to_embed += f" {text[:500]}"

                    embedding = self.generate_embedding(text_to_embed)
                    if not embedding:
                        continue

                    point = PointStruct(
                        id=node_id,
                        vector=embedding,
                        payload={
                            "node_id": node_id,
                            "project_id": project_id,
                            "title": title,
                            "summary": summary or "",
                            "type": node_type,
                        },
                    )
                    points.append(point)

                if points:
                    self.client.upsert(collection_name=collection_name, points=points)
                    upserted_count += len(points)

            logger.info(f"Batch upserted {upserted_count} knowledge nodes for project {project_id}")
            return upserted_count

        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            return upserted_count

    def upsert_document_chunks(
        self,
        project_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        collection_type: str = "documents",
    ) -> int:
        """
        Upsert document chunks for RAG ingestion.
        Returns number of chunks successfully upserted.
        """
        if not self.client or not self.embedding_model:
            return 0

        collection_name = self._get_collection_name(project_id, collection_type)
        if not self.ensure_collection(project_id, collection_type):
            return 0

        try:
            points = []
            for i, chunk_data in enumerate(chunks):
                chunk_id = chunk_data.get("chunk_id", f"{document_id}_chunk_{i}")
                content = chunk_data.get("content", "")
                metadata = chunk_data.get("metadata", {})

                if not content:
                    continue

                embedding = self.generate_embedding(content)
                if not embedding:
                    continue

                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload={
                        "document_id": document_id,
                        "project_id": project_id,
                        "content": content,
                        "chunk_index": i,
                        **metadata,
                    },
                )
                points.append(point)

            if points:
                self.client.upsert(collection_name=collection_name, points=points)
                logger.info(f"Upserted {len(points)} document chunks for document {document_id}")
                return len(points)

            return 0

        except Exception as e:
            logger.error(f"Failed to upsert document chunks: {e}")
            return 0

    def search_documents(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        collection_type: str = "documents",
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search document chunks by similarity.
        Returns list of matching chunks with scores.
        """
        if not self.client or not self.embedding_model:
            return []

        collection_name = self._get_collection_name(project_id, collection_type)
        if not self.client.collection_exists(collection_name):
            return []

        try:
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []

            # Build filter if document_id specified
            filter_condition = None
            if document_id:
                filter_condition = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])

            search_kwargs = {
                "collection_name": collection_name,
                "query_vector": query_embedding,
                "limit": limit,
            }
            if filter_condition:
                search_kwargs["query_filter"] = filter_condition

            results = self.client.search(**search_kwargs)

            return [
                {
                    "chunk_id": r.payload.get("chunk_id", r.id),
                    "document_id": r.payload.get("document_id"),
                    "content": r.payload.get("content"),
                    "chunk_index": r.payload.get("chunk_index"),
                    "score": r.score,
                    "metadata": {k: v for k, v in r.payload.items() if k not in ["content", "chunk_index", "document_id", "chunk_id"]},
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []


# Global instance
qdrant_service = QdrantService()

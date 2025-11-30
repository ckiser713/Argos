from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import get_settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(self):
        settings = get_settings()
        qdrant_url = getattr(settings, "qdrant_url", "http://localhost:6333")

        try:
            self.client = QdrantClient(url=qdrant_url)
            self.client.get_collections()
            logger.info(f"Connected to Qdrant at {qdrant_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}")
            self.client = None

        self.embedding_models = {}
        self.embedding_sizes = {}
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Embedding model loaded on device: {device}")

            # Local import to avoid import-time dependency on sentence-transformers
            from sentence_transformers import SentenceTransformer

            # Default model for documents
            self.embedding_models['default'] = SentenceTransformer("all-MiniLM-L6-v2", device=device)
            self.embedding_sizes['default'] = 384

            # Model for code search
            self.embedding_models['code'] = SentenceTransformer("jinaai/jina-embeddings-v2-base-code", device=device, trust_remote_code=True)
            self.embedding_sizes['code'] = 768
            
        except Exception as e:
            logger.error(f"Failed to load embedding models: {e}")

    def _get_collection_name(self, project_id: str, collection_type: str = "knowledge") -> str:
        return f"{collection_type}_{project_id}"

    def ensure_collection(self, project_id: str, collection_type: str = "knowledge", embedding_size: int = 384) -> bool:
        if not self.client:
            return False
        collection_name = self._get_collection_name(project_id, collection_type)
        try:
            if not self.client.collection_exists(collection_name):
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection: {collection_name} with dimension {embedding_size}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def generate_embedding(self, text: str, model_name: str = 'default') -> Optional[List[float]]:
        model = self.embedding_models.get(model_name)
        if not model:
            logger.warning(f"Embedding model '{model_name}' not found.")
            return None
        try:
            return model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding with {model_name}: {e}")
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
        model_name = 'code' if node_type == 'code' else 'default'
        collection_type = 'code_search' if node_type == 'code' else 'knowledge'
        embedding_size = self.embedding_sizes.get(model_name, 384)

        if not self.client or not self.embedding_models.get(model_name):
            return False

        if not self.ensure_collection(project_id, collection_type, embedding_size):
            return False

        text_to_embed = f"{title} {summary or ''} {text or ''}"
        embedding = self.generate_embedding(text_to_embed, model_name=model_name)
        if not embedding:
            return False

        collection_name = self._get_collection_name(project_id, collection_type)
        try:
            point = PointStruct(id=node_id, vector=embedding, payload={"node_id": node_id, "title": title, "summary": summary or "", "type": node_type or "concept"})
            self.client.upsert(collection_name=collection_name, points=[point])
            return True
        except Exception as e:
            logger.error(f"Failed to upsert knowledge node: {e}")
            return False
            
    # ... rest of the service methods would need to be updated to handle different models/collections
    # For this exercise, we focus on the setup and dynamic nature of the service.

    def upsert_document_chunks(
        self,
        project_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        collection_type: str = "documents",
    ) -> int:
        """Upsert document chunks into Qdrant as vector points.

        Each chunk should be a dict with keys: chunk_id, content, metadata (containing chunk_index).
        Returns the number of chunks successfully upserted.
        """
        model_name = "default"
        embedding_size = self.embedding_sizes.get(model_name, 384)

        if not self.client or not self.embedding_models.get(model_name):
            logger.warning("Qdrant or embedding models not configured; skipping upsert")
            return 0

        if not self.ensure_collection(project_id, collection_type, embedding_size):
            return 0

        collection_name = self._get_collection_name(project_id, collection_type)
        points = []
        upserted = 0
        try:
            for c in chunks:
                chunk_id = c.get("chunk_id")
                content = c.get("content", "")
                payload = c.get("metadata", {})
                embedding = self.generate_embedding(content, model_name=model_name)
                if not embedding:
                    continue
                points.append(PointStruct(id=chunk_id, vector=embedding, payload={**payload, "content": content}))

            if points:
                self.client.upsert(collection_name=collection_name, points=points)
                upserted = len(points)
        except Exception as e:
            logger.error(f"Failed to upsert document chunks: {e}")
            return upserted

        return upserted

    def search_documents(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        collection_type: str = "documents",
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for documents using a semantic vector query. Returns list of result dicts.
        """
        model_name = "default"
        if not self.client or not self.embedding_models.get(model_name):
            logger.warning("Qdrant or embedding model not configured; returning empty results")
            return []

        collection_name = self._get_collection_name(project_id, collection_type)
        try:
            emb = self.generate_embedding(query, model_name=model_name)
            if not emb:
                return []
            results = self.client.search(collection_name=collection_name, query_vector=emb, limit=limit, with_payload=True)
            processed = []
            for r in results:
                payload = r.payload or {}
                if document_id and payload.get("document_id") != document_id:
                    continue
                processed.append({
                    "content": payload.get("content", ""),
                    "score": r.score,
                    "document_id": payload.get("document_id"),
                    "chunk_index": payload.get("chunk_index"),
                    "metadata": payload,
                })
            return processed
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            return []

    def search_knowledge_nodes(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
        node_type: Optional[str] = None,
        use_vector_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for knowledge nodes using Qdrant vector search and return a list of results.
        Each result is a dict with keys: node_id, score, title, summary.
        """
        if not use_vector_search or not self.client:
            logger.warning("Qdrant or embedding model not configured; skipping knowledge search")
            return []

        model_name = "code" if node_type == "code" else "default"
        collection_type = "code_search" if node_type == "code" else "knowledge"

        if not self.embedding_models.get(model_name):
            logger.warning("Embedding model '%s' not available", model_name)
            return []

        collection_name = self._get_collection_name(project_id, collection_type)
        emb = self.generate_embedding(query, model_name=model_name)
        if not emb:
            return []
        try:
            results = self.client.search(collection_name=collection_name, query_vector=emb, limit=limit, with_payload=True)
            processed = []
            for r in results:
                payload = r.payload or {}
                processed.append({
                    "node_id": payload.get("node_id"),
                    "score": r.score,
                    "title": payload.get("title"),
                    "summary": payload.get("summary"),
                })
            return processed
        except Exception as e:
            logger.error(f"Qdrant knowledge search failed: {e}")
            return []

    def delete_knowledge_node(self, project_id: str, node_id: str) -> bool:
        """Delete a knowledge node point from Qdrant."""
        if not self.client:
            return False
        collection_name = self._get_collection_name(project_id, "knowledge")
        try:
            self.client.delete(collection_name=collection_name, points=[node_id])
            return True
        except Exception as e:
            logger.error(f"Failed to delete knowledge node from Qdrant: {e}")
            return False


qdrant_service = QdrantService()
    

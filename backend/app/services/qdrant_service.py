from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

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


qdrant_service = QdrantService()

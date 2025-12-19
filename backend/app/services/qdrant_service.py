from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import Settings, get_settings
from app.observability import record_embedding_call

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(
        self,
        client: Optional[QdrantClient] = None,
        settings: Optional[Settings] = None,
        sentence_transformer_cls: Optional[Any] = None,
    ):
        self.settings = settings or get_settings()
        self.client: Optional[QdrantClient] = None
        self.client_error: Optional[str] = None
        self.embedding_models: Dict[str, Any] = {}
        self.embedding_sizes: Dict[str, int] = {}
        self.embedding_error: Optional[str] = None
        self.code_embedding_error: Optional[str] = None
        self.device: Optional[str] = None
        self.sentence_transformer_cls = sentence_transformer_cls

        self._connect_client(client_override=client)
        if getattr(self.settings, "require_embeddings", False):
            self.load_embeddings()

    def _connect_client(self, client_override: Optional[QdrantClient] = None) -> None:
        """Connect to Qdrant once at service startup."""
        if client_override is not None:
            self.client = client_override
            try:
                self.client.get_collections()
                logger.info(
                    "Connected to injected Qdrant client",
                    extra={"event": "qdrant.connect.success", "source": "override"},
                )
            except Exception as exc:
                self.client_error = str(exc)
                logger.warning(
                    "Failed to validate injected Qdrant client: %s",
                    exc,
                    extra={"event": "qdrant.connect.failed", "source": "override"},
                )
            return

        qdrant_url = getattr(self.settings, "qdrant_url", "http://localhost:6333")
        try:
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=getattr(self.settings, "qdrant_api_key", None),
            )
            self.client.get_collections()
            logger.info(
                "Connected to Qdrant",
                extra={"event": "qdrant.connect.success", "url": qdrant_url},
            )
        except Exception as exc:
            self.client_error = str(exc)
            logger.warning(
                "Failed to connect to Qdrant: %s",
                exc,
                extra={"event": "qdrant.connect.failed", "url": qdrant_url},
            )
            self.client = None

    def _resolve_device(self) -> str:
        """Determine the device used for embeddings."""
        preference = (getattr(self.settings, "embedding_device", "auto") or "auto").lower()
        if preference == "cpu":
            return "cpu"

        try:
            import torch  # type: ignore
        except Exception as exc:
            self.embedding_error = f"torch not available: {exc}"
            logger.error(
                "Embedding device resolution failed: %s",
                exc,
                extra={"event": "embeddings.device.failed"},
            )
            return "cpu"

        if preference in {"cuda", "gpu"} and torch.cuda.is_available():
            return "cuda"
        if preference == "rocm" and torch.cuda.is_available():
            return "cuda"
        if preference == "auto" and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load_embeddings(self, force_reload: bool = False) -> None:
        """Load embedding models with structured error handling."""
        if self.embedding_models and not force_reload:
            return

        self.embedding_models = {}
        self.embedding_sizes = {}
        self.embedding_error = None
        self.code_embedding_error = None

        try:
            SentenceTransformer = self.sentence_transformer_cls
            if SentenceTransformer is None:
                from sentence_transformers import SentenceTransformer as _SentenceTransformer

                SentenceTransformer = _SentenceTransformer
        except Exception as exc:
            self.embedding_error = f"sentence-transformers import failed: {exc}"
            logger.error(
                "Embedding stack import failed: %s",
                exc,
                extra={"event": "embeddings.load.failed", "stage": "import"},
            )
            return

        self.device = self._resolve_device()

        try:
            default_model = SentenceTransformer(
                self.settings.embedding_model_name,
                device=self.device,
            )
            self.embedding_models["default"] = default_model
            self.embedding_sizes["default"] = default_model.get_sentence_embedding_dimension()
            logger.info(
                "Loaded default embedding model",
                extra={
                    "event": "embeddings.load.success",
                    "model": self.settings.embedding_model_name,
                    "device": self.device,
                    "dimension": self.embedding_sizes["default"],
                },
            )
        except Exception as exc:
            self.embedding_error = (
                f"Failed to load embedding model '{self.settings.embedding_model_name}': {exc}"
            )
            logger.error(
                self.embedding_error,
                extra={
                    "event": "embeddings.load.failed",
                    "model": self.settings.embedding_model_name,
                    "device": self.device,
                },
            )
            return

        code_model_name = getattr(self.settings, "code_embedding_model_name", None)
        if code_model_name:
            try:
                code_model = SentenceTransformer(
                    code_model_name,
                    device=self.device,
                    trust_remote_code=True,
                )
                self.embedding_models["code"] = code_model
                self.embedding_sizes["code"] = code_model.get_sentence_embedding_dimension()
                logger.info(
                    "Loaded code embedding model",
                    extra={
                        "event": "embeddings.load.success",
                        "model": code_model_name,
                        "device": self.device,
                        "dimension": self.embedding_sizes["code"],
                    },
                )
            except Exception as exc:
                self.code_embedding_error = (
                    f"Failed to load code embedding model '{code_model_name}': {exc}"
                )
                logger.warning(
                    self.code_embedding_error,
                    extra={
                        "event": "embeddings.load.partial_failure",
                        "model": code_model_name,
                        "device": self.device,
                    },
                )

    def can_generate_embeddings(self) -> bool:
        return bool(self.embedding_models.get("default")) and self.embedding_error is None

    def get_health(self) -> Dict[str, Any]:
        return {
            "ready": self.client is not None and self.can_generate_embeddings(),
            "can_generate_embeddings": self.can_generate_embeddings(),
            "qdrant_connected": self.client is not None,
            "device": self.device,
            "default_model": getattr(self.settings, "embedding_model_name", None),
            "code_model": getattr(self.settings, "code_embedding_model_name", None),
            "embedding_error": self.embedding_error,
            "code_embedding_error": self.code_embedding_error,
            "client_error": self.client_error,
        }

    def ensure_ready(self, require_embeddings: bool = False) -> Dict[str, Any]:
        """Validate that Qdrant and embeddings are available."""
        if not self.client:
            msg = self.client_error or "Qdrant client not initialized"
            logger.warning(
                "Qdrant unavailable: %s",
                msg,
                extra={"event": "qdrant.unavailable"},
            )
            if require_embeddings:
                raise RuntimeError(f"Qdrant unavailable: {msg}")

        if not self.embedding_models or self.embedding_error:
            # Reload embeddings if none are currently cached or previous load failed
            self.load_embeddings(force_reload=True)

        if require_embeddings and not self.can_generate_embeddings():
            err = self.embedding_error or "Embedding models not loaded"
            logger.error(
                "Embedding models required but unavailable: %s",
                err,
                extra={"event": "embeddings.unavailable"},
            )
            raise RuntimeError(err)

        return self.get_health()

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
        if not self.embedding_models and not self.embedding_error:
            # Lazy load if embeddings were not preloaded
            self.load_embeddings()

        model = self.embedding_models.get(model_name)
        if self.embedding_error:
            logger.error(
                "Embedding stack unavailable: %s",
                self.embedding_error,
                extra={"event": "embeddings.encode.failed", "model": model_name},
            )
            record_embedding_call(model_name, False)
            return None
        if not model:
            logger.warning(f"Embedding model '{model_name}' not found.")
            record_embedding_call(model_name, False)
            return None
        try:
            vector = model.encode(text, show_progress_bar=False)
            if hasattr(vector, "tolist"):
                vector = vector.tolist()
            record_embedding_call(model_name, True)
            return list(vector)
        except Exception as e:
            logger.error(f"Failed to generate embedding with {model_name}: {e}")
            record_embedding_call(model_name, False)
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

        if not self.embedding_models and not self.embedding_error:
            self.load_embeddings()
        if self.embedding_error:
            logger.warning("Embedding stack unavailable: %s", self.embedding_error)
            return False
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
            # Normalize node id to a UUID that Qdrant accepts, keep original as payload
            try:
                # If already a valid UUID string, keep it
                uuid.UUID(node_id)
                normalized_id = node_id
            except Exception:
                normalized_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(node_id)))

            payload = {"node_id": node_id, "title": title, "summary": summary or "", "type": node_type or "concept"}
            payload["source_node_id"] = node_id
            point = PointStruct(id=normalized_id, vector=embedding, payload=payload)
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

        if not self.embedding_models and not self.embedding_error:
            self.load_embeddings()
        if self.embedding_error:
            logger.warning("Embedding stack unavailable: %s", self.embedding_error)
            return 0
        if not self.client or not self.embedding_models.get(model_name):
            logger.warning("Qdrant or embedding models not configured; skipping upsert")
            return 0

        if not self.ensure_collection(project_id, collection_type, embedding_size):
            return 0

        collection_name = self._get_collection_name(project_id, collection_type)
        points = []
        upserted = 0
        def _normalize_point_id(point_id: str) -> str:
            try:
                uuid.UUID(point_id)
                return point_id
            except Exception:
                return str(uuid.uuid5(uuid.NAMESPACE_URL, str(point_id)))

        try:
            for c in chunks:
                chunk_id = c.get("chunk_id")
                content = c.get("content", "")
                payload = c.get("metadata", {})
                embedding = self.generate_embedding(content, model_name=model_name)
                if not embedding:
                    continue
                normalized_chunk_id = _normalize_point_id(chunk_id)
                # Keep original chunk id so the rest of the system can map
                payload["source_chunk_id"] = chunk_id
                points.append(PointStruct(id=normalized_chunk_id, vector=embedding, payload={**payload, "content": content}))

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
        if not self.embedding_models and not self.embedding_error:
            self.load_embeddings()
        if self.embedding_error:
            logger.warning("Embedding stack unavailable: %s", self.embedding_error)
            return []
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

        if not self.embedding_models and not self.embedding_error:
            self.load_embeddings()
        if self.embedding_error:
            logger.warning("Embedding stack unavailable: %s", self.embedding_error)
            return []
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
    

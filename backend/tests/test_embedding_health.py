import math
import types

import pytest

from app.config import Settings
from app.services.qdrant_service import QdrantService


class FakeQdrantClient:
    """Lightweight in-memory stub for QdrantClient used in unit tests."""

    def __init__(self):
        self.collections = {}
        self.points = {}

    def get_collections(self):
        return types.SimpleNamespace(
            collections=[types.SimpleNamespace(name=name) for name in self.collections.keys()]
        )

    def collection_exists(self, name: str) -> bool:
        return name in self.collections

    def create_collection(self, collection_name: str, vectors_config) -> None:  # pragma: no cover - simple stub
        self.collections[collection_name] = vectors_config

    def upsert(self, collection_name: str, points):
        store = self.points.setdefault(collection_name, [])
        for point in points:
            store.append(
                {
                    "id": getattr(point, "id", None),
                    "vector": list(getattr(point, "vector", []) or []),
                    "payload": getattr(point, "payload", {}) or {},
                }
            )

    def search(self, collection_name: str, query_vector, limit: int = 5, with_payload: bool = True):
        docs = self.points.get(collection_name, [])
        results = []
        for doc in docs:
            score = _cosine_similarity(query_vector, doc["vector"])
            results.append(types.SimpleNamespace(payload=doc["payload"], score=score))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]


def _cosine_similarity(a, b) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _dummy_sentence_transformer(dim: int = 3):
    class DummyModel:
        def __init__(self, name, device=None, trust_remote_code=False):
            self.name = name
            self.device = device
            self._dim = dim

        def encode(self, text, show_progress_bar=False):
            base = float(len(text) % 5)
            return [base + i for i in range(self._dim)]

        def get_sentence_embedding_dimension(self):
            return self._dim

    return DummyModel


def _make_settings(**overrides) -> Settings:
    defaults = {
        "embedding_model_name": "dummy-default",
        "code_embedding_model_name": "dummy-code",
        "embedding_device": "cpu",
        "require_embeddings": False,
        "auth_secret": "test-secret",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_embedding_load_success():
    settings = _make_settings()
    service = QdrantService(
        client=FakeQdrantClient(),
        settings=settings,
        sentence_transformer_cls=_dummy_sentence_transformer(dim=4),
    )
    service.load_embeddings(force_reload=True)

    assert service.can_generate_embeddings()
    assert service.embedding_sizes["default"] == 4
    assert service.device == "cpu"


def test_embedding_load_failure_raises_when_required():
    class FailingModel:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    settings = _make_settings(require_embeddings=True)
    service = QdrantService(
        client=FakeQdrantClient(),
        settings=settings,
        sentence_transformer_cls=FailingModel,
    )
    service.load_embeddings(force_reload=True)

    assert not service.can_generate_embeddings()
    with pytest.raises(RuntimeError):
        service.ensure_ready(require_embeddings=True)


def test_qdrant_roundtrip_with_stubbed_client():
    settings = _make_settings()
    client = FakeQdrantClient()
    service = QdrantService(
        client=client,
        settings=settings,
        sentence_transformer_cls=_dummy_sentence_transformer(dim=3),
    )
    service.load_embeddings(force_reload=True)

    chunks = [
        {
            "chunk_id": "c1",
            "content": "hello world",
            "metadata": {"document_id": "doc1", "chunk_index": 0},
        }
    ]

    upserted = service.upsert_document_chunks("proj1", "doc1", chunks)
    assert upserted == 1

    results = service.search_documents("proj1", "hello", limit=1)
    assert results
    assert results[0]["document_id"] == "doc1"
    assert results[0]["chunk_index"] == 0


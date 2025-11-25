import uuid

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer


class RagService:
    def __init__(self):
        # Connect to Qdrant (ensure container is running)
        self.client = QdrantClient("http://localhost:6333")
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.collection = "cortex_vectors"

        # Init Collection
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            if self.collection not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
                )
        except Exception as e:
            # If Qdrant is not available, continue without it
            import logging
            logging.warning(f"Could not initialize Qdrant collection: {e}")

    def ingest_document(self, text: str, metadata: dict):
        """Chunk text and upload to Qdrant."""
        # Simple overlapping chunker
        chunk_size = 500
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - 50)]

        points = []
        for chunk in chunks:
            vector = self.model.encode(chunk).tolist()
            points.append(
                models.PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"content": chunk, **metadata})
            )

        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query: str, limit: int = 5):
        vector = self.model.encode(query).tolist()
        results = self.client.search(collection_name=self.collection, query_vector=vector, limit=limit)
        return [{"content": r.payload["content"], "score": r.score} for r in results]


rag_service = RagService()

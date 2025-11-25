# app/services/rag_service.py
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

class RagService:
    def __init__(self):
        # Connect to Qdrant (ensure container is running)
        self.client = QdrantClient("http://localhost:6333")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = "cortex_vectors"
        
        # Init Collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def ingest_document(self, text: str, metadata: dict):
        """Chunk text and upload to Qdrant."""
        # Simple overlapping chunker
        chunk_size = 500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - 50)]
        
        points = []
        for chunk in chunks:
            vector = self.model.encode(chunk).tolist()
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={"content": chunk, **metadata}
            ))
            
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query: str, limit: int = 5):
        vector = self.model.encode(query).tolist()
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit
        )
        return [{"content": r.payload["content"], "score": r.score} for r in results]

rag_service = RagService()
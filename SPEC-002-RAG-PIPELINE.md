Goal: Implement real document ingestion and vector retrieval.

Markdown

# SPEC-002: RAG Ingestion Pipeline

## Problem
`ingest_service.py` is a stub. Files uploaded are not read, parsed, or searchable.

## Tech Stack
- **Vector DB:** Qdrant (Docker) or ChromaDB (Local).
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (runs locally on CPU/GPU).
- **Parser:** `pypdf` for PDFs, standard IO for code files.

## Implementation Guide

### 1. New Dependencies
Add to `pyproject.toml`:
`sentence-transformers`, `qdrant-client`, `pypdf`, `langchain-text-splitters`

### 2. Create `backend/app/services/rag_service.py`
```python
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
3. Wire into IngestService
Modify backend/app/services/ingest_service.py to call rag_service.ingest_document when a job is processed.
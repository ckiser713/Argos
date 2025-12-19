# Feature Specification: Qdrant Vector Database Integration

## Overview
Implementation specification for integrating Qdrant vector database for knowledge graph, embeddings, and semantic search capabilities.

## Current State
- Qdrant mentioned in architecture but not integrated
- Knowledge service uses placeholder implementation
- No vector search capabilities
- No embedding storage

## Target State
- Qdrant integrated for vector storage
- Embeddings generated and stored
- Semantic search working
- Knowledge graph backed by Qdrant
- Efficient similarity search

## Requirements

### Functional Requirements
1. Store embeddings in Qdrant
2. Perform semantic search
3. Store knowledge nodes with vectors
4. Query by similarity
5. Hybrid search (keyword + vector)

### Non-Functional Requirements
1. Fast search (< 200ms)
2. Support 100K+ vectors
3. Efficient indexing
4. Connection pooling

## Technical Design

### Qdrant Setup
- Docker container for Qdrant
- Collection per project (or shared with project filter)
- Index configuration for performance

### Integration Points

#### 1. Knowledge Service
- Store node embeddings
- Search by similarity
- Update embeddings on node update

#### 2. RAG Service
- Store document chunks with embeddings
- Retrieve similar chunks
- Hybrid search support

#### 3. Embedding Service
- Generate embeddings using model
- Batch processing
- Caching embeddings

### Database Schema
- Qdrant collections for vectors
- PostgreSQL for metadata
- Link vectors to metadata via IDs

### Implementation

#### Qdrant Client
```python
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="knowledge_nodes",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Insert vectors
client.upsert(
    collection_name="knowledge_nodes",
    points=[
        PointStruct(
            id=node_id,
            vector=embedding,
            payload={"title": title, "type": type}
        )
    ]
)

# Search
results = client.search(
    collection_name="knowledge_nodes",
    query_vector=query_embedding,
    limit=10
)
```

## Testing Strategy

### Unit Tests
- Test Qdrant client operations
- Test embedding generation
- Test search functionality

### Integration Tests
- Test with Qdrant container
- Test search performance
- Test data consistency

## Implementation Steps

1. Set up Qdrant infrastructure
2. Create Qdrant client wrapper
3. Integrate with knowledge service
4. Integrate with RAG service
5. Add embedding generation
6. Write tests
7. Performance testing

## Success Criteria

1. Qdrant integrated
2. Embeddings stored and retrieved
3. Semantic search works
4. Performance meets requirements
5. Tests pass

## Notes

- Consider embedding model selection
- Optimize collection configuration
- Monitor Qdrant performance
- Consider backup strategies


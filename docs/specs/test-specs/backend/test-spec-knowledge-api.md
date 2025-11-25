# Test Specification: Knowledge API

## Purpose
Comprehensive test specification for Knowledge API endpoints, covering graph operations, node/edge management, search functionality, and project-scoped operations.

## Test Cases

### 1. List Knowledge Nodes

#### 1.1 List Nodes with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/knowledge-graph/nodes`
- **Setup**: Create 40 knowledge nodes
- **Action**: GET request with default pagination
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<KnowledgeNode>`
  - Includes `items`, `nextCursor`, `total`
  - Default limit applied

#### 1.2 List Nodes with Type Filter
- **Setup**: Create nodes with different types (concept, document, code, ticket)
- **Action**: GET request with `type=concept`
- **Expected**: 
  - Returns only nodes of specified type
  - Other types excluded

#### 1.3 List Nodes with Search Query
- **Setup**: Create nodes with various text content
- **Action**: GET request with `q=search_term`
- **Expected**: 
  - Returns nodes matching search term
  - Search is case-insensitive
  - Searches across title, summary, text fields

### 2. Get Knowledge Graph Snapshot

#### 2.1 Get Default Graph View
- **Endpoint**: `GET /api/projects/{projectId}/knowledge-graph`
- **Setup**: Create nodes and edges
- **Action**: GET request without view parameter
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ nodes: KnowledgeNode[], edges: KnowledgeEdge[], generatedAt: string }`
  - All nodes and edges included
  - `generatedAt` timestamp present

#### 2.2 Get Ideas View
- **Action**: GET request with `view=ideas`
- **Expected**: 
  - Returns only nodes related to ideas
  - Filters nodes by type or tags
  - Includes relevant edges

#### 2.3 Get Tickets View
- **Action**: GET request with `view=tickets`
- **Expected**: 
  - Returns only ticket-related nodes
  - Includes ticket-to-ticket relationships
  - Filters appropriately

#### 2.4 Get Docs View
- **Action**: GET request with `view=docs`
- **Expected**: 
  - Returns only document-related nodes
  - Includes document-to-concept relationships
  - Filters appropriately

#### 2.5 Get Graph with Focus Node
- **Setup**: Create graph with node A connected to B, C, D
- **Action**: GET request with `focusNodeId=A.id`
- **Expected**: 
  - Returns focused node
  - Returns immediate neighbors (B, C, D)
  - Returns edges connecting to neighbors
  - May exclude distant nodes (TBD)

### 3. Get Node Details

#### 3.1 Get Existing Node
- **Endpoint**: `GET /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}`
- **Setup**: Create a knowledge node
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete node object
  - All fields present (id, title, summary, type, tags, metadata)

#### 3.2 Get Non-Existent Node
- **Action**: GET request with invalid nodeId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Knowledge node not found"

#### 3.3 Get Node from Wrong Project
- **Setup**: Create node in project A
- **Action**: GET request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

### 4. Get Node Neighbors

#### 4.1 Get Neighbors for Node
- **Endpoint**: `GET /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}/neighbors`
- **Setup**: Create node A connected to B, C, D
- **Action**: GET request for node A
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ node: KnowledgeNode, neighbors: KnowledgeNode[], edges: KnowledgeEdge[] }`
  - Includes all neighbors (B, C, D)
  - Includes edges connecting to neighbors

#### 4.2 Get Neighbors for Isolated Node
- **Setup**: Create node with no connections
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns node with empty neighbors array
  - Returns empty edges array

#### 4.3 Get Neighbors with Depth Limit
- **Setup**: Create chain A → B → C → D
- **Action**: GET request with `depth=1` (if supported)
- **Expected**: 
  - Returns only immediate neighbors (B)
  - Does not include C or D

### 5. Search Knowledge Nodes

#### 5.1 Search by Text Query
- **Endpoint**: `POST /api/projects/{projectId}/knowledge/search`
- **Setup**: Create nodes with various text content
- **Request Body**: `{ query: "machine learning", limit: 10 }`
- **Expected**: 
  - Status code: `200 OK`
  - Returns nodes matching query
  - Results ordered by relevance score
  - Respects limit parameter

#### 5.2 Search with Type Filter
- **Request Body**: `{ query: "algorithm", type: "concept" }`
- **Expected**: 
  - Returns only concept nodes matching query
  - Other types excluded

#### 5.3 Search with Tag Filter
- **Request Body**: `{ query: "python", tags: ["code", "backend"] }`
- **Expected**: 
  - Returns nodes matching query AND having specified tags
  - Logical AND for tags

#### 5.4 Empty Search Results
- **Request Body**: `{ query: "nonexistent_term_xyz" }`
- **Expected**: 
  - Status code: `200 OK`
  - Returns empty array
  - No error thrown

#### 5.5 Search with Vector Similarity
- **Request Body**: `{ query: "neural networks", useVectorSearch: true }`
- **Expected**: 
  - Uses vector similarity search (if implemented)
  - Returns semantically similar nodes
  - Results include similarity scores

### 6. Create Knowledge Node

#### 6.1 Create Node with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/knowledge-graph/nodes`
- **Request Body**: `{ title: "New Concept", type: "concept", summary: "Description" }`
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `KnowledgeNode`
  - Node has generated `id`
  - Timestamps set

#### 6.2 Create Node with Tags
- **Request Body**: `{ title: "Node", type: "concept", tags: ["tag1", "tag2"] }`
- **Expected**: 
  - Tags saved correctly
  - Tags accessible for filtering

#### 6.3 Create Node with Metadata
- **Request Body**: `{ title: "Node", type: "document", metadata: { source: "pdf", page: 42 } }`
- **Expected**: 
  - Metadata saved correctly
  - Metadata accessible in responses

#### 6.4 Create Node with Invalid Type
- **Request Body**: `{ title: "Node", type: "invalid_type" }`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid type

### 7. Update Knowledge Node

#### 7.1 Update Node Title
- **Endpoint**: `PATCH /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}`
- **Setup**: Create a node
- **Request Body**: `{ title: "Updated Title" }`
- **Expected**: 
  - Status code: `200 OK`
  - Title updated
  - Other fields unchanged
  - `updatedAt` timestamp updated

#### 7.2 Update Node Tags
- **Request Body**: `{ tags: ["new_tag1", "new_tag2"] }`
- **Expected**: 
  - Tags replaced (not merged)
  - Old tags removed
  - New tags saved

#### 7.3 Update Node Summary
- **Request Body**: `{ summary: "Updated summary text" }`
- **Expected**: 
  - Summary updated
  - Text search reflects changes

#### 7.4 Update Non-Existent Node
- **Action**: PATCH request with invalid nodeId
- **Expected**: 
  - Status code: `404 Not Found`

### 8. Create Knowledge Edge

#### 8.1 Create Edge Between Nodes
- **Endpoint**: `POST /api/projects/{projectId}/knowledge-graph/edges`
- **Setup**: Create nodes A and B
- **Request Body**: `{ source: A.id, target: B.id, type: "relates_to", weight: 0.8 }`
- **Expected**: 
  - Status code: `201 Created`
  - Edge created successfully
  - Graph structure updated

#### 8.2 Create Edge with Invalid Source
- **Request Body**: `source` pointing to non-existent node
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid source

#### 8.3 Create Edge with Invalid Target
- **Request Body**: `target` pointing to non-existent node
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid target

#### 8.4 Create Edge with Invalid Type
- **Request Body**: `type` not in allowed enum values
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid type

#### 8.5 Create Duplicate Edge
- **Setup**: Edge A → B already exists
- **Action**: Attempt to create same edge
- **Expected**: 
  - Status code: `409 Conflict`
  - Error message indicates edge already exists

### 9. Delete Knowledge Edge

#### 9.1 Delete Existing Edge
- **Endpoint**: `DELETE /api/projects/{projectId}/knowledge-graph/edges/{edgeId}`
- **Setup**: Create an edge
- **Action**: DELETE request
- **Expected**: 
  - Status code: `200 OK` or `204 No Content`
  - Edge removed from database
  - Graph structure updated

#### 9.2 Delete Non-Existent Edge
- **Action**: DELETE request with invalid edgeId
- **Expected**: 
  - Status code: `404 Not Found`

### 10. Graph Traversal

#### 10.1 Find Path Between Nodes
- **Endpoint**: `GET /api/projects/{projectId}/knowledge-graph/path?from={nodeId}&to={nodeId}`
- **Setup**: Create path A → B → C → D
- **Action**: Find path from A to D
- **Expected**: 
  - Status code: `200 OK`
  - Returns path: [A, B, C, D]
  - Returns edges: [A→B, B→C, C→D]

#### 10.2 Find Path When No Path Exists
- **Setup**: Create disconnected nodes A and B
- **Action**: Find path from A to B
- **Expected**: 
  - Status code: `404 Not Found` or `200 OK` with empty path
  - Error message indicates no path exists

#### 10.3 Find Shortest Path
- **Setup**: Multiple paths exist between A and D
- **Action**: Find shortest path
- **Expected**: 
  - Returns shortest path (fewest edges)
  - Uses appropriate algorithm (BFS)

## Test Data

### Sample KnowledgeNode
```json
{
  "id": "kn_123",
  "projectId": "proj_abc",
  "title": "Machine Learning Concepts",
  "summary": "Overview of ML algorithms and techniques",
  "text": "Full text content...",
  "type": "concept",
  "tags": ["ml", "ai", "algorithms"],
  "metadata": {
    "source": "research_paper.pdf",
    "page": 42,
    "confidence": 0.95
  },
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

### Sample KnowledgeEdge
```json
{
  "id": "ke_456",
  "projectId": "proj_abc",
  "source": "kn_123",
  "target": "kn_124",
  "type": "relates_to",
  "weight": 0.85,
  "label": "Similar concept",
  "createdAt": "2024-01-15T10:05:00Z"
}
```

## Edge Cases

1. **Very Large Graphs**: Projects with 10,000+ nodes
2. **Dense Graphs**: Nodes with 1000+ connections
3. **Sparse Graphs**: Many isolated nodes
4. **Circular References**: Self-referencing edges (if allowed)
5. **Unicode Content**: Nodes with Unicode characters
6. **Very Long Text**: Nodes with text > 1MB
7. **Special Characters**: Tags and queries with special characters
8. **Concurrent Updates**: Multiple users updating same graph

## Dependencies

- FastAPI TestClient
- Database fixtures (projects, nodes, edges)
- Vector search service (for similarity search)
- Graph traversal library (for path finding)
- Mock knowledge service (for unit tests)

## Test Implementation Notes

- Use pytest fixtures for graph setup
- Mock vector search for search tests
- Test graph operations at both API and service layers
- Verify database constraints and indexes
- Test performance with large graphs
- Use transaction rollback for data cleanup
- Mock external services (Qdrant, embedding service)


# API Specification: Knowledge Endpoints

## Overview
Complete API specification for knowledge graph endpoints, covering graph operations, node/edge CRUD, search, and project-scoped routes.

## Endpoints

### GET /api/projects/{projectId}/knowledge-graph

Get knowledge graph snapshot.

#### Query Parameters
- `view` (string, optional): View preset ('default', 'ideas', 'tickets', 'docs')
- `focusNodeId` (string, optional): Focus on specific node and neighbors

#### Responses

**200 OK**
```json
{
  "nodes": [
    {
      "id": "kn_123",
      "projectId": "proj_abc",
      "title": "Machine Learning Concepts",
      "summary": "Overview of ML algorithms",
      "type": "concept",
      "tags": ["ml", "ai"]
    }
  ],
  "edges": [
    {
      "id": "ke_456",
      "source": "kn_123",
      "target": "kn_124",
      "type": "relates_to",
      "weight": 0.85
    }
  ],
  "generatedAt": "2024-01-15T10:00:00Z"
}
```

---

### GET /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}

Get single knowledge node.

#### Responses

**200 OK**
```json
{
  "id": "kn_123",
  "projectId": "proj_abc",
  "title": "Machine Learning Concepts",
  "summary": "Overview of ML algorithms",
  "text": "Full text content...",
  "type": "concept",
  "tags": ["ml", "ai", "algorithms"],
  "metadata": {
    "source": "research_paper.pdf",
    "page": 42
  },
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

**404 Not Found**
```json
{
  "detail": "Knowledge node not found"
}
```

---

### GET /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}/neighbors

Get neighbors for a node.

#### Responses

**200 OK**
```json
{
  "node": {
    "id": "kn_123",
    "title": "Machine Learning Concepts"
  },
  "neighbors": [
    {
      "id": "kn_124",
      "title": "Neural Networks"
    }
  ],
  "edges": [
    {
      "id": "ke_456",
      "source": "kn_123",
      "target": "kn_124",
      "type": "relates_to"
    }
  ]
}
```

---

### POST /api/projects/{projectId}/knowledge-graph/nodes

Create knowledge node.

#### Request Body
```json
{
  "title": "New Concept",
  "summary": "Description",
  "text": "Full text...",
  "type": "concept",
  "tags": ["tag1", "tag2"],
  "metadata": {
    "source": "document.pdf"
  }
}
```

#### Responses

**201 Created**
- Returns created node

**400 Bad Request**
```json
{
  "detail": "Invalid type: invalid_type"
}
```

---

### PATCH /api/projects/{projectId}/knowledge-graph/nodes/{nodeId}

Update knowledge node.

#### Request Body (all fields optional)
```json
{
  "title": "Updated Title",
  "tags": ["new_tag1", "new_tag2"],
  "summary": "Updated summary"
}
```

#### Responses

**200 OK**
- Returns updated node

**404 Not Found**
```json
{
  "detail": "Knowledge node not found"
}
```

---

### POST /api/projects/{projectId}/knowledge-graph/edges

Create knowledge edge.

#### Request Body
```json
{
  "source": "kn_123",
  "target": "kn_124",
  "type": "relates_to",
  "weight": 0.85,
  "label": "Similar concept"
}
```

#### Responses

**201 Created**
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

**400 Bad Request**
```json
{
  "detail": "Invalid source node"
}
```

**409 Conflict**
```json
{
  "detail": "Edge already exists"
}
```

---

### DELETE /api/projects/{projectId}/knowledge-graph/edges/{edgeId}

Delete knowledge edge.

#### Responses

**200 OK**
```json
{
  "success": true
}
```

**404 Not Found**
```json
{
  "detail": "Knowledge edge not found"
}
```

---

### POST /api/projects/{projectId}/knowledge/search

Search knowledge nodes.

#### Request Body
```json
{
  "query": "machine learning",
  "type": "concept",
  "tags": ["ml", "ai"],
  "limit": 10,
  "useVectorSearch": true
}
```

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "kn_123",
      "title": "Machine Learning Concepts",
      "summary": "Overview of ML algorithms",
      "score": 0.95,
      "type": "concept"
    }
  ],
  "total": 25
}
```

---

## Error Responses

### 400 Bad Request
- Invalid node references
- Invalid type values
- Invalid search parameters

### 404 Not Found
- Node/edge not found
- Project not found

### 409 Conflict
- Duplicate edges

## Notes

- All endpoints are project-scoped
- Graph operations support large graphs efficiently
- Search supports both text and vector similarity
- Node types: concept, document, code, ticket


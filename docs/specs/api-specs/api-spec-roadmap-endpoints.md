# API Specification: Roadmap Endpoints

## Overview
Complete API specification for roadmap endpoints, covering full CRUD operations for nodes and edges, graph operations, and project-scoped routes.

## Endpoints

### GET /api/projects/{projectId}/roadmap/nodes

List roadmap nodes with filtering and pagination.

#### Path Parameters
- `projectId` (string, required): Project ID

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results (1-100)
- `status` (string, optional): Filter by status (PENDING, ACTIVE, COMPLETE, BLOCKED)
- `laneId` (string, optional): Filter by lane ID

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "node_123",
      "projectId": "proj_abc",
      "label": "Phase 1: Setup",
      "description": "Initial project setup",
      "status": "ACTIVE",
      "priority": "HIGH",
      "startDate": "2024-01-15T00:00:00Z",
      "targetDate": "2024-02-15T00:00:00Z",
      "dependsOnIds": ["node_122"],
      "laneId": "lane_backend",
      "createdAt": "2024-01-10T10:00:00Z",
      "updatedAt": "2024-01-12T14:30:00Z"
    }
  ],
  "nextCursor": "cursor_abc123",
  "total": 45
}
```

---

### POST /api/projects/{projectId}/roadmap/nodes

Create a new roadmap node.

#### Request Body
```json
{
  "label": "Phase 1: Setup",
  "description": "Initial project setup",
  "status": "PENDING",
  "priority": "HIGH",
  "startDate": "2024-01-15T00:00:00Z",
  "targetDate": "2024-02-15T00:00:00Z",
  "dependsOnIds": ["node_122"],
  "laneId": "lane_backend",
  "ideaId": "idea_456",
  "ticketId": "ticket_789",
  "missionControlTaskId": "task_012"
}
```

#### Responses

**201 Created**
```json
{
  "id": "node_123",
  "projectId": "proj_abc",
  "label": "Phase 1: Setup",
  "status": "PENDING",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid dependencies: node_999 does not exist"
}
```

---

### GET /api/projects/{projectId}/roadmap/nodes/{nodeId}

Get a single roadmap node.

#### Responses

**200 OK**
```json
{
  "id": "node_123",
  "projectId": "proj_abc",
  "label": "Phase 1: Setup",
  "description": "Initial project setup",
  "status": "ACTIVE",
  "priority": "HIGH",
  "startDate": "2024-01-15T00:00:00Z",
  "targetDate": "2024-02-15T00:00:00Z",
  "dependsOnIds": ["node_122"],
  "laneId": "lane_backend",
  "createdAt": "2024-01-10T10:00:00Z",
  "updatedAt": "2024-01-12T14:30:00Z"
}
```

**404 Not Found**
```json
{
  "detail": "Roadmap node not found"
}
```

---

### PATCH /api/projects/{projectId}/roadmap/nodes/{nodeId}

Update a roadmap node.

#### Request Body (all fields optional)
```json
{
  "label": "Updated Label",
  "status": "ACTIVE",
  "priority": "MEDIUM",
  "dependsOnIds": ["node_122", "node_124"]
}
```

#### Responses

**200 OK**
- Returns updated node

**400 Bad Request**
```json
{
  "detail": "Circular dependency detected"
}
```

**404 Not Found**
```json
{
  "detail": "Roadmap node not found"
}
```

---

### GET /api/projects/{projectId}/roadmap/edges

List roadmap edges.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "edge_456",
      "projectId": "proj_abc",
      "fromNodeId": "node_123",
      "toNodeId": "node_124",
      "kind": "depends_on",
      "label": "Must complete before",
      "createdAt": "2024-01-10T10:05:00Z"
    }
  ],
  "nextCursor": null,
  "total": 12
}
```

---

### POST /api/projects/{projectId}/roadmap/edges

Create a roadmap edge.

#### Request Body
```json
{
  "fromNodeId": "node_123",
  "toNodeId": "node_124",
  "kind": "depends_on",
  "label": "Must complete before"
}
```

#### Responses

**201 Created**
```json
{
  "id": "edge_456",
  "projectId": "proj_abc",
  "fromNodeId": "node_123",
  "toNodeId": "node_124",
  "kind": "depends_on",
  "label": "Must complete before",
  "createdAt": "2024-01-15T10:05:00Z"
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid source node: node_999 does not exist"
}
```

**409 Conflict**
```json
{
  "detail": "Edge already exists"
}
```

---

### DELETE /api/projects/{projectId}/roadmap/edges/{edgeId}

Delete a roadmap edge.

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
  "detail": "Roadmap edge not found"
}
```

---

### GET /api/projects/{projectId}/roadmap

Get complete roadmap graph.

#### Responses

**200 OK**
```json
{
  "nodes": [
    {
      "id": "node_123",
      "label": "Phase 1",
      "status": "ACTIVE"
    }
  ],
  "edges": [
    {
      "id": "edge_456",
      "source": "node_123",
      "target": "node_124",
      "kind": "depends_on"
    }
  ],
  "generatedAt": "2024-01-15T10:00:00Z"
}
```

---

## Error Responses

### 400 Bad Request
- Invalid dependencies
- Circular dependencies
- Invalid node references
- Invalid status transitions

### 404 Not Found
- Node/edge not found
- Project not found

### 409 Conflict
- Duplicate edges
- Invalid state transitions

## Notes

- All endpoints are project-scoped
- Graph validation ensures DAG structure (no cycles)
- Status transitions validated
- Dependencies must exist and belong to same project


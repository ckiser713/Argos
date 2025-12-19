# Test Specification: Roadmap API

## Purpose
Comprehensive test specification for Roadmap API endpoints, covering full CRUD operations, graph validation, node/edge management, and project-scoped operations.

## Test Cases

### 1. List Roadmap Nodes

#### 1.1 List Nodes with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/roadmap/nodes`
- **Setup**: Create 30 roadmap nodes
- **Action**: GET request with default pagination
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<RoadmapNode>`
  - Includes `items`, `nextCursor`, `total`
  - Default limit applied (e.g., 50)

#### 1.2 List Nodes with Status Filter
- **Setup**: Create nodes with different statuses (PENDING, ACTIVE, COMPLETE, BLOCKED)
- **Action**: GET request with `status=ACTIVE`
- **Expected**: 
  - Returns only nodes with status `ACTIVE`
  - Other statuses excluded

#### 1.3 List Nodes with Lane Filter
- **Setup**: Create nodes in different lanes
- **Action**: GET request with `laneId={laneId}`
- **Expected**: 
  - Returns only nodes in specified lane
  - Other lanes excluded

#### 1.4 List Nodes with Combined Filters
- **Action**: GET request with `status=ACTIVE&laneId={id}`
- **Expected**: 
  - Returns nodes matching ALL criteria
  - Logical AND behavior

### 2. Create Roadmap Node

#### 2.1 Create Node with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/roadmap/nodes`
- **Request Body**: `{ label: "Phase 1", description: "Initial setup" }`
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `RoadmapNode`
  - Node has generated `id`
  - Default status assigned (e.g., `PENDING`)
  - `createdAt` and `updatedAt` timestamps set

#### 2.2 Create Node with All Fields
- **Request Body**: Complete node with all optional fields
- **Expected**: 
  - All fields saved correctly
  - Dates parsed correctly (ISO-8601)
  - Dependencies validated (exist and belong to project)

#### 2.3 Create Node with Invalid Dependencies
- **Request Body**: `dependsOnIds` containing non-existent node IDs
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid dependencies

#### 2.4 Create Node with Cross-Project Dependencies
- **Setup**: Node exists in project B
- **Request Body**: `dependsOnIds` containing node from project B
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates dependency must be in same project

#### 2.5 Create Node with Circular Dependencies (Direct)
- **Setup**: Create node A
- **Request Body**: Create node B depending on A, then update A to depend on B
- **Expected**: 
  - Status code: `400 Bad Request` (on update)
  - Error message indicates circular dependency detected

#### 2.6 Create Node with Circular Dependencies (Indirect)
- **Setup**: A → B → C
- **Action**: Attempt to create D → A (would create A → B → C → D → A)
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates circular dependency detected

### 3. Get Roadmap Node

#### 3.1 Get Existing Node
- **Endpoint**: `GET /api/projects/{projectId}/roadmap/nodes/{nodeId}`
- **Setup**: Create a roadmap node
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete node object
  - All fields present

#### 3.2 Get Non-Existent Node
- **Action**: GET request with invalid nodeId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Roadmap node not found"

#### 3.3 Get Node from Wrong Project
- **Setup**: Create node in project A
- **Action**: GET request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

### 4. Update Roadmap Node

#### 4.1 Update Node Status
- **Endpoint**: `PATCH /api/projects/{projectId}/roadmap/nodes/{nodeId}`
- **Setup**: Create node with status `PENDING`
- **Request Body**: `{ status: "ACTIVE" }`
- **Expected**: 
  - Status code: `200 OK`
  - Node status updated
  - `updatedAt` timestamp updated

#### 4.2 Update Node with Partial Fields
- **Request Body**: `{ label: "New Label", priority: "HIGH" }`
- **Expected**: 
  - Only specified fields updated
  - Other fields unchanged

#### 4.3 Update Node Dependencies
- **Setup**: Create nodes A, B, C
- **Request Body**: Update A with `dependsOnIds: [B.id, C.id]`
- **Expected**: 
  - Dependencies updated
  - Graph structure reflects changes

#### 4.4 Update Node with Invalid Status Transition
- **Setup**: Create node with status `COMPLETE`
- **Request Body**: `{ status: "PENDING" }`
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates invalid status transition
  - Status remains `COMPLETE`

#### 4.5 Update Non-Existent Node
- **Action**: PATCH request with invalid nodeId
- **Expected**: 
  - Status code: `404 Not Found`

### 5. List Roadmap Edges

#### 5.1 List Edges with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/roadmap/edges`
- **Setup**: Create 20 edges
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<RoadmapEdge>`
  - Includes pagination metadata

#### 5.2 List Edges for Specific Nodes
- **Action**: GET request with filters for source/target nodes
- **Expected**: 
  - Returns edges matching filter criteria
  - Useful for graph traversal

### 6. Create Roadmap Edge

#### 6.1 Create Edge Between Existing Nodes
- **Endpoint**: `POST /api/projects/{projectId}/roadmap/edges`
- **Setup**: Create nodes A and B
- **Request Body**: `{ fromNodeId: A.id, toNodeId: B.id, kind: "depends_on" }`
- **Expected**: 
  - Status code: `201 Created`
  - Edge created successfully
  - Graph structure updated

#### 6.2 Create Edge with Invalid Source Node
- **Request Body**: `fromNodeId` pointing to non-existent node
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid source node

#### 6.3 Create Edge with Invalid Target Node
- **Request Body**: `toNodeId` pointing to non-existent node
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid target node

#### 6.4 Create Edge Between Nodes from Different Projects
- **Setup**: Node A in project 1, Node B in project 2
- **Request Body**: Edge from A to B
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates nodes must be in same project

#### 6.5 Create Duplicate Edge
- **Setup**: Edge A → B already exists
- **Action**: Attempt to create same edge again
- **Expected**: 
  - Status code: `409 Conflict`
  - Error message indicates edge already exists

#### 6.6 Create Self-Referencing Edge
- **Setup**: Create node A
- **Request Body**: Edge from A to A
- **Expected**: 
  - Status code: `400 Bad Request` or allowed (TBD)
  - Error message if not allowed

### 7. Delete Roadmap Edge

#### 7.1 Delete Existing Edge
- **Endpoint**: `DELETE /api/projects/{projectId}/roadmap/edges/{edgeId}`
- **Setup**: Create an edge
- **Action**: DELETE request
- **Expected**: 
  - Status code: `200 OK` or `204 No Content`
  - Response: `{ success: true }`
  - Edge removed from database

#### 7.2 Delete Non-Existent Edge
- **Action**: DELETE request with invalid edgeId
- **Expected**: 
  - Status code: `404 Not Found`

#### 7.3 Delete Edge from Wrong Project
- **Setup**: Create edge in project A
- **Action**: DELETE request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

### 8. Graph Validation

#### 8.1 Validate DAG Structure
- **Setup**: Create nodes and edges forming valid DAG
- **Action**: Verify graph is acyclic
- **Expected**: 
  - Graph validation passes
  - No circular dependencies

#### 8.2 Detect Cycles in Graph
- **Setup**: Create cycle: A → B → C → A
- **Action**: Attempt to create final edge
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates cycle detected

#### 8.3 Validate Node Dependencies Exist
- **Action**: Create node with `dependsOnIds` referencing non-existent nodes
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message lists invalid dependencies

#### 8.4 Validate Edge Consistency
- **Action**: Create edge where target node doesn't exist
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid target

### 9. Roadmap Graph Operations

#### 9.1 Get Complete Roadmap Graph
- **Endpoint**: `GET /api/projects/{projectId}/roadmap`
- **Setup**: Create nodes and edges
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `RoadmapGraph` with all nodes and edges
  - Graph structure is valid DAG

#### 9.2 Get Roadmap for Empty Project
- **Action**: GET request for project with no roadmap
- **Expected**: 
  - Status code: `200 OK`
  - Returns graph with empty nodes and edges arrays

## Test Data

### Sample RoadmapNode
```json
{
  "id": "node_123",
  "projectId": "proj_abc",
  "label": "Phase 1: Setup",
  "description": "Initial project setup and configuration",
  "status": "ACTIVE",
  "priority": "HIGH",
  "startDate": "2024-01-15T00:00:00Z",
  "targetDate": "2024-02-15T00:00:00Z",
  "dependsOnIds": ["node_122"],
  "laneId": "lane_backend",
  "ideaId": null,
  "ticketId": null,
  "missionControlTaskId": null,
  "createdAt": "2024-01-10T10:00:00Z",
  "updatedAt": "2024-01-12T14:30:00Z"
}
```

### Sample RoadmapEdge
```json
{
  "id": "edge_456",
  "projectId": "proj_abc",
  "fromNodeId": "node_123",
  "toNodeId": "node_124",
  "kind": "depends_on",
  "label": "Must complete before",
  "createdAt": "2024-01-10T10:05:00Z"
}
```

## Edge Cases

1. **Very Large Graphs**: Projects with 1000+ nodes
2. **Deep Dependency Chains**: Chains of 50+ dependencies
3. **Wide Dependency Trees**: Nodes with 100+ dependencies
4. **Concurrent Updates**: Multiple users updating same roadmap
5. **Date Validation**: Invalid date formats, past dates for targets
6. **Priority Values**: Invalid priority enum values
7. **Status Transitions**: All valid and invalid transitions
8. **Unicode Labels**: Nodes with Unicode characters in labels

## Dependencies

- FastAPI TestClient
- Database fixtures (projects, nodes, edges)
- Graph validation library (for cycle detection)
- Mock roadmap service (for unit tests)

## Test Implementation Notes

- Use pytest fixtures for graph setup
- Implement cycle detection algorithm for validation tests
- Test graph operations at both API and service layers
- Verify database constraints (foreign keys, unique constraints)
- Test transaction rollback on errors
- Mock date/time for consistent test results


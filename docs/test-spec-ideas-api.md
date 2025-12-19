# Test Specification: Ideas API

## Purpose
Comprehensive test specification for Ideas API endpoints, covering project-scoped routes, filtering, pagination, idea candidates, clusters, tickets, and mission control tasks.

## Test Cases

### 1. List Idea Candidates

#### 1.1 List Candidates with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/ideas/candidates`
- **Setup**: Create 30 idea candidates
- **Action**: GET request with default pagination
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<IdeaCandidate>`
  - Includes `items`, `nextCursor`, `total`
  - Default limit applied

#### 1.2 List Candidates with Status Filter
- **Setup**: Create candidates with different statuses
- **Action**: GET request with `status=ACTIVE`
- **Expected**: 
  - Returns only candidates with specified status
  - Other statuses excluded

#### 1.3 List Candidates with Type Filter
- **Setup**: Create candidates with different types (feature, bug, improvement, research)
- **Action**: GET request with `type=feature`
- **Expected**: 
  - Returns only candidates of specified type
  - Other types excluded

#### 1.4 List Candidates with Combined Filters
- **Action**: GET request with `status=ACTIVE&type=feature`
- **Expected**: 
  - Returns candidates matching ALL criteria
  - Logical AND behavior

### 2. Create Idea Candidate

#### 2.1 Create Candidate with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/ideas/candidates`
- **Request Body**: 
  ```json
  {
    "type": "feature",
    "summary": "Add user authentication system"
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `IdeaCandidate`
  - Candidate has generated `id`
  - Default status assigned (e.g., `INBOX`)
  - Timestamps set

#### 2.2 Create Candidate with All Fields
- **Request Body**: Complete candidate with optional fields
- **Expected**: 
  - All fields saved correctly
  - Source references validated (if applicable)
  - Confidence score within valid range (0-1)

#### 2.3 Create Candidate with Invalid Type
- **Request Body**: `type: "invalid_type"`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid type

#### 2.4 Create Candidate with Invalid Confidence
- **Request Body**: `confidence: 1.5` (outside 0-1 range)
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid confidence

#### 2.5 Create Candidate with Source References
- **Request Body**: Includes `sourceLogIds`, `sourceChannel`, `sourceUser`
- **Expected**: 
  - Source references stored correctly
  - Can trace back to origin

### 3. Update Idea Candidate

#### 3.1 Update Candidate Status
- **Endpoint**: `PATCH /api/projects/{projectId}/ideas/candidates/{ideaId}`
- **Setup**: Create candidate with status `INBOX`
- **Request Body**: `{ status: "ACTIVE" }`
- **Expected**: 
  - Status code: `200 OK`
  - Status updated
  - Other fields unchanged
  - `updatedAt` timestamp updated

#### 3.2 Update Candidate Summary
- **Request Body**: `{ summary: "Updated summary" }`
- **Expected**: 
  - Summary updated
  - Change tracked (if audit log exists)

#### 3.3 Update Candidate Confidence
- **Request Body**: `{ confidence: 0.95 }`
- **Expected**: 
  - Confidence updated
  - Value validated (0-1 range)

#### 3.4 Update Non-Existent Candidate
- **Action**: PATCH request with invalid ideaId
- **Expected**: 
  - Status code: `404 Not Found`

### 4. List Idea Clusters

#### 4.1 List Clusters with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/ideas/clusters`
- **Setup**: Create 20 idea clusters
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<IdeaCluster>`
  - Includes pagination metadata

#### 4.2 List Clusters with Idea Counts
- **Expected**: 
  - Each cluster includes count of associated ideas
  - Counts are accurate

### 5. Create Idea Cluster

#### 5.1 Create Cluster with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/ideas/clusters`
- **Request Body**: 
  ```json
  {
    "label": "Authentication Features",
    "description": "All authentication-related ideas"
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `IdeaCluster`
  - Cluster has generated `id`
  - Timestamps set

#### 5.2 Create Cluster with Ideas
- **Request Body**: Includes `ideaIds: ["idea_1", "idea_2"]`
- **Expected**: 
  - Ideas associated with cluster
  - Ideas accessible via cluster

#### 5.3 Create Cluster with Color
- **Request Body**: Includes `color: "#FF5733"`
- **Expected**: 
  - Color stored correctly
  - Color used in UI (if applicable)

#### 5.4 Create Cluster with Invalid Idea IDs
- **Request Body**: `ideaIds` containing non-existent ideas
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid idea IDs

### 6. Update Idea Cluster

#### 6.1 Update Cluster Label
- **Endpoint**: `PATCH /api/projects/{projectId}/ideas/clusters/{clusterId}`
- **Setup**: Create cluster
- **Request Body**: `{ label: "Updated Label" }`
- **Expected**: 
  - Label updated
  - Other fields unchanged

#### 6.2 Update Cluster Ideas
- **Request Body**: `{ ideaIds: ["idea_3", "idea_4"] }`
- **Expected**: 
  - Ideas replaced (not merged)
  - Old associations removed
  - New associations created

#### 6.3 Update Non-Existent Cluster
- **Action**: PATCH request with invalid clusterId
- **Expected**: 
  - Status code: `404 Not Found`

### 7. List Tickets

#### 7.1 List Tickets with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/ideas/tickets`
- **Setup**: Create 25 tickets
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<IdeaTicket>`
  - Includes pagination metadata

#### 7.2 List Tickets with Status Filter
- **Setup**: Create tickets with different statuses
- **Action**: GET request with `status=ACTIVE`
- **Expected**: 
  - Returns only tickets with specified status
  - Other statuses excluded

#### 7.3 List Tickets with Priority Filter
- **Action**: GET request with `priority=HIGH` (if supported)
- **Expected**: 
  - Returns only tickets with specified priority
  - Other priorities excluded

### 8. Create Ticket from Idea

#### 8.1 Create Ticket with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/ideas/tickets`
- **Setup**: Create idea candidate
- **Request Body**: 
  ```json
  {
    "ideaId": "idea_123",
    "title": "Implement OAuth2",
    "originStory": "Discussed in chat log #45",
    "category": "feature"
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `IdeaTicket`
  - Ticket linked to idea
  - Default status assigned
  - Timestamps set

#### 8.2 Create Ticket with All Fields
- **Request Body**: Complete ticket with optional fields
- **Expected**: 
  - All fields saved correctly
  - Task summaries parsed (if applicable)
  - Repo hints stored

#### 8.3 Create Ticket with Invalid Idea ID
- **Request Body**: `ideaId` pointing to non-existent idea
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid idea

#### 8.4 Create Ticket with Source Quotes
- **Request Body**: Includes `sourceQuotes: "User said: 'We need this feature'" `
- **Expected**: 
  - Quotes stored correctly
  - Quotes accessible in ticket details

### 9. Update Ticket

#### 9.1 Update Ticket Status
- **Endpoint**: `PATCH /api/projects/{projectId}/ideas/tickets/{ticketId}`
- **Setup**: Create ticket
- **Request Body**: `{ status: "IN_PROGRESS" }`
- **Expected**: 
  - Status updated
  - Status transition validated (if applicable)

#### 9.2 Update Ticket Priority
- **Request Body**: `{ priority: "HIGH" }`
- **Expected**: 
  - Priority updated
  - Priority value validated

#### 9.3 Update Ticket Title
- **Request Body**: `{ title: "Updated Title" }`
- **Expected**: 
  - Title updated
  - Change tracked

#### 9.4 Update Non-Existent Ticket
- **Action**: PATCH request with invalid ticketId
- **Expected**: 
  - Status code: `404 Not Found`

### 10. List Mission Control Tasks

#### 10.1 List Tasks with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/tasks`
- **Setup**: Create 30 mission control tasks
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<MissionControlTask>`
  - Includes pagination metadata

#### 10.2 List Tasks with Column Filter
- **Setup**: Create tasks in different columns (backlog, todo, in_progress, done)
- **Action**: GET request with `column=todo`
- **Expected**: 
  - Returns only tasks in specified column
  - Other columns excluded

#### 10.3 List Tasks with Origin Filter
- **Setup**: Create tasks with different origins (repo, chat, pdf)
- **Action**: GET request with `origin=chat`
- **Expected**: 
  - Returns only tasks with specified origin
  - Other origins excluded

#### 10.4 List Tasks with Combined Filters
- **Action**: GET request with `column=todo&origin=chat`
- **Expected**: 
  - Returns tasks matching ALL criteria
  - Logical AND behavior

### 11. Create Mission Control Task

#### 11.1 Create Task with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/tasks`
- **Request Body**: 
  ```json
  {
    "title": "Refactor authentication module",
    "origin": "repo"
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `MissionControlTask`
  - Task has generated `id`
  - Default column assigned (e.g., `backlog`)
  - Timestamps set

#### 11.2 Create Task with Context Files
- **Request Body**: Includes `context: [{ name: "auth.ts", type: "code" }]`
- **Expected**: 
  - Context files stored correctly
  - Context accessible in task details

#### 11.3 Create Task with Linked Entities
- **Request Body**: Includes `ideaId`, `ticketId`, `roadmapNodeId`
- **Expected**: 
  - Links stored correctly
  - Can navigate to linked entities

#### 11.4 Create Task with Invalid Origin
- **Request Body**: `origin: "invalid_origin"`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid origin

### 12. Update Mission Control Task

#### 12.1 Update Task Column (Drag-Drop)
- **Endpoint**: `PATCH /api/projects/{projectId}/tasks/{taskId}`
- **Setup**: Create task in `backlog` column
- **Request Body**: `{ column: "todo" }`
- **Expected**: 
  - Status code: `200 OK`
  - Column updated
  - Task appears in new column
  - `updatedAt` timestamp updated

#### 12.2 Update Task Priority
- **Request Body**: `{ priority: "HIGH" }`
- **Expected**: 
  - Priority updated
  - Change reflected in UI

#### 12.3 Update Task Title
- **Request Body**: `{ title: "Updated Title" }`
- **Expected**: 
  - Title updated
  - Change tracked

#### 12.4 Update Non-Existent Task
- **Action**: PATCH request with invalid taskId
- **Expected**: 
  - Status code: `404 Not Found`

## Test Data

### Sample IdeaCandidate
```json
{
  "id": "idea_123",
  "projectId": "proj_abc",
  "type": "feature",
  "summary": "Add user authentication system",
  "sourceLogIds": ["log_456"],
  "sourceChannel": "chat",
  "sourceUser": "user_789",
  "confidence": 0.85,
  "status": "ACTIVE",
  "clusterId": null,
  "createdAt": "2024-01-15T10:00:00Z"
}
```

### Sample IdeaCluster
```json
{
  "id": "cluster_123",
  "projectId": "proj_abc",
  "label": "Authentication Features",
  "description": "All authentication-related ideas",
  "color": "#FF5733",
  "ideaIds": ["idea_1", "idea_2"],
  "priority": "HIGH",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

### Sample IdeaTicket
```json
{
  "id": "ticket_123",
  "projectId": "proj_abc",
  "ideaId": "idea_456",
  "clusterId": null,
  "title": "Implement OAuth2",
  "description": "Add OAuth2 authentication support",
  "status": "ACTIVE",
  "priority": "HIGH",
  "category": "feature",
  "originStory": "Discussed in chat log #45",
  "impliedTaskSummaries": ["Setup OAuth2 provider", "Configure routes"],
  "repoHints": ["auth/", "middleware/"],
  "sourceQuotes": "User said: 'We need OAuth2'",
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

### Sample MissionControlTask
```json
{
  "id": "task_123",
  "projectId": "proj_abc",
  "title": "Refactor authentication module",
  "origin": "repo",
  "confidence": 0.9,
  "column": "todo",
  "context": [
    { "name": "auth.ts", "type": "code" },
    { "name": "middleware.ts", "type": "code" }
  ],
  "priority": "HIGH",
  "ideaId": null,
  "ticketId": null,
  "roadmapNodeId": null,
  "createdAt": "2024-01-15T10:00:00Z",
  "updatedAt": "2024-01-15T10:00:00Z"
}
```

## Edge Cases

1. **Very Large Lists**: 1000+ ideas, tickets, or tasks
2. **Complex Clusters**: Clusters with 100+ ideas
3. **Circular References**: Tickets referencing each other (if applicable)
4. **Concurrent Updates**: Multiple users updating same entity
5. **Invalid Status Transitions**: Attempting invalid status changes
6. **Unicode Content**: Entities with Unicode characters
7. **Very Long Summaries**: Summaries > 10KB
8. **Missing Required Fields**: Requests missing required fields

## Dependencies

- FastAPI TestClient
- Database fixtures (projects, ideas, clusters, tickets, tasks)
- Mock idea service (for unit tests)
- Project intel service (for idea extraction)

## Test Implementation Notes

- Use pytest fixtures for entity setup
- Test project-scoped routes (all routes under `/projects/{projectId}/`)
- Verify database constraints and foreign keys
- Test both unit (service layer) and integration (API layer) levels
- Use transaction rollback for data cleanup
- Test pagination with various limits
- Verify filtering logic correctness
- Test concurrent operations for race conditions


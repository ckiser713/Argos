# API Specification: Ideas Endpoints

## Overview
Complete API specification for ideas endpoints, covering project-scoped routes structure, idea candidates, clusters, tickets, and mission control tasks.

## Endpoints

### GET /api/projects/{projectId}/ideas/candidates

List idea candidates.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results
- `status` (string, optional): Filter by status
- `type` (string, optional): Filter by type (feature, bug, improvement, research)

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "idea_123",
      "projectId": "proj_abc",
      "type": "feature",
      "summary": "Add user authentication system",
      "status": "ACTIVE",
      "confidence": 0.85,
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ],
  "nextCursor": "cursor_abc123",
  "total": 150
}
```

---

### POST /api/projects/{projectId}/ideas/candidates

Create idea candidate.

#### Request Body
```json
{
  "type": "feature",
  "summary": "Add user authentication system",
  "sourceLogIds": ["log_456"],
  "sourceChannel": "chat",
  "sourceUser": "user_789",
  "confidence": 0.85
}
```

#### Responses

**201 Created**
- Returns created candidate

---

### PATCH /api/projects/{projectId}/ideas/candidates/{ideaId}

Update idea candidate.

#### Request Body (all fields optional)
```json
{
  "status": "ACTIVE",
  "confidence": 0.95,
  "summary": "Updated summary"
}
```

#### Responses

**200 OK**
- Returns updated candidate

**404 Not Found**
```json
{
  "detail": "Idea candidate not found"
}
```

---

### GET /api/projects/{projectId}/ideas/clusters

List idea clusters.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "cluster_123",
      "projectId": "proj_abc",
      "label": "Authentication Features",
      "description": "All authentication-related ideas",
      "color": "#FF5733",
      "ideaIds": ["idea_1", "idea_2"],
      "priority": "HIGH",
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ],
  "nextCursor": null,
  "total": 10
}
```

---

### POST /api/projects/{projectId}/ideas/clusters

Create idea cluster.

#### Request Body
```json
{
  "label": "Authentication Features",
  "description": "All authentication-related ideas",
  "color": "#FF5733",
  "ideaIds": ["idea_1", "idea_2"],
  "priority": "HIGH"
}
```

#### Responses

**201 Created**
- Returns created cluster

---

### GET /api/projects/{projectId}/ideas/tickets

List idea tickets.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results
- `status` (string, optional): Filter by status

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "ticket_123",
      "projectId": "proj_abc",
      "ideaId": "idea_456",
      "title": "Implement OAuth2",
      "status": "ACTIVE",
      "priority": "HIGH",
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ],
  "nextCursor": null,
  "total": 45
}
```

---

### POST /api/projects/{projectId}/ideas/tickets

Create ticket from idea.

#### Request Body
```json
{
  "ideaId": "idea_456",
  "title": "Implement OAuth2",
  "originStory": "Discussed in chat log #45",
  "category": "feature",
  "impliedTaskSummaries": ["Setup OAuth2 provider"],
  "repoHints": ["auth/"],
  "sourceQuotes": "User said: 'We need OAuth2'"
}
```

#### Responses

**201 Created**
- Returns created ticket

---

### GET /api/projects/{projectId}/tasks

List mission control tasks.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results
- `column` (string, optional): Filter by column (backlog, todo, in_progress, done)
- `origin` (string, optional): Filter by origin (repo, chat, pdf)

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "task_123",
      "projectId": "proj_abc",
      "title": "Refactor authentication module",
      "origin": "repo",
      "confidence": 0.9,
      "column": "todo",
      "context": [
        { "name": "auth.ts", "type": "code" }
      ],
      "priority": "HIGH",
      "createdAt": "2024-01-15T10:00:00Z"
    }
  ],
  "nextCursor": null,
  "total": 30
}
```

---

### POST /api/projects/{projectId}/tasks

Create mission control task.

#### Request Body
```json
{
  "title": "Refactor authentication module",
  "origin": "repo",
  "confidence": 0.9,
  "column": "backlog",
  "context": [
    { "name": "auth.ts", "type": "code" }
  ],
  "priority": "HIGH",
  "ideaId": "idea_123",
  "ticketId": "ticket_456"
}
```

#### Responses

**201 Created**
- Returns created task

---

### PATCH /api/projects/{projectId}/tasks/{taskId}

Update mission control task.

#### Request Body (all fields optional)
```json
{
  "column": "todo",
  "priority": "HIGH",
  "title": "Updated title"
}
```

#### Responses

**200 OK**
- Returns updated task

**404 Not Found**
```json
{
  "detail": "Mission control task not found"
}
```

---

## Error Responses

### 400 Bad Request
- Invalid idea ID
- Invalid cluster ID
- Invalid ticket ID
- Invalid column value

### 404 Not Found
- Idea/candidate/cluster/ticket/task not found
- Project not found

## Notes

- All endpoints are project-scoped
- Ideas flow: Candidate → Cluster → Ticket → Task
- Status transitions validated
- Column values: backlog, todo, in_progress, done
- Origin values: repo, chat, pdf


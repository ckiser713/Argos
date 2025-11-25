# API Specification: Agents Endpoints

## Overview
Complete API specification for agent endpoints, covering run details, steps, messages, cancel operations, and project-scoped routes.

## Endpoints

### GET /api/projects/{projectId}/agent-runs/{runId}

Get single agent run.

#### Responses

**200 OK**
```json
{
  "id": "run_123",
  "projectId": "proj_abc",
  "workflowId": "wf_456",
  "status": "RUNNING",
  "inputQuery": "Analyze the authentication system",
  "outputSummary": null,
  "startedAt": "2024-01-15T10:00:00Z",
  "finishedAt": null,
  "contextItemIds": ["ctx_1", "ctx_2"]
}
```

**404 Not Found**
```json
{
  "detail": "Agent run not found"
}
```

---

### GET /api/projects/{projectId}/agent-runs/{runId}/steps

List steps for agent run.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "step_789",
      "runId": "run_123",
      "stepNumber": 1,
      "nodeId": "retrieve_docs",
      "status": "COMPLETED",
      "input": "Query: authentication",
      "output": "Retrieved 5 documents",
      "error": null,
      "durationMs": 1250,
      "startedAt": "2024-01-15T10:00:05Z",
      "completedAt": "2024-01-15T10:00:06.25Z"
    }
  ],
  "nextCursor": null,
  "total": 15
}
```

---

### GET /api/projects/{projectId}/agent-runs/{runId}/node-states

List node states for agent run.

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "runId": "run_123",
      "nodeId": "retrieve",
      "status": "COMPLETED",
      "progress": 1.0,
      "messages": ["Retrieved documents successfully"],
      "startedAt": "2024-01-15T10:00:05Z",
      "completedAt": "2024-01-15T10:00:06Z",
      "error": null
    }
  ]
}
```

---

### GET /api/projects/{projectId}/agent-runs/{runId}/messages

List messages for agent run.

#### Query Parameters
- `cursor` (string, optional): Pagination cursor
- `limit` (integer, optional, default: 50): Maximum number of results

#### Responses

**200 OK**
```json
{
  "items": [
    {
      "id": "msg_456",
      "runId": "run_123",
      "role": "user",
      "content": "Can you provide more details?",
      "contextItemIds": ["ctx_1"],
      "createdAt": "2024-01-15T10:05:00Z"
    }
  ],
  "nextCursor": null,
  "total": 20
}
```

---

### POST /api/projects/{projectId}/agent-runs/{runId}/messages

Append user message to agent run.

#### Request Body
```json
{
  "content": "Can you provide more details?",
  "contextItemIds": ["ctx_1", "ctx_2"]
}
```

#### Responses

**201 Created**
```json
{
  "id": "msg_456",
  "runId": "run_123",
  "role": "user",
  "content": "Can you provide more details?",
  "contextItemIds": ["ctx_1", "ctx_2"],
  "createdAt": "2024-01-15T10:05:00Z"
}
```

**400 Bad Request**
```json
{
  "detail": "Run cannot accept messages. Current status: CANCELLED"
}
```

---

### POST /api/projects/{projectId}/agent-runs/{runId}/cancel

Cancel agent run.

#### Responses

**200 OK**
```json
{
  "id": "run_123",
  "status": "CANCELLED",
  "finishedAt": "2024-01-15T10:30:00Z"
}
```

**400 Bad Request**
```json
{
  "detail": "Run cannot be cancelled. Current status: COMPLETED"
}
```

**404 Not Found**
```json
{
  "detail": "Agent run not found"
}
```

---

## Error Responses

### 400 Bad Request
- Invalid run state
- Invalid message content
- Cannot cancel completed run

### 404 Not Found
- Agent run not found
- Step not found
- Message not found

## Notes

- All endpoints are project-scoped
- Steps ordered by stepNumber (chronological)
- Messages ordered by createdAt (chronological)
- Cancelling stops background execution
- Appending message may restart run if completed


# API Specification: Streaming Endpoints

## Overview
Complete API specification for WebSocket/SSE streaming endpoints, covering ingest job events, agent run events, and workflow node events.

## WebSocket Endpoints

### WebSocket /api/stream/projects/{projectId}/ingest/{jobId}

Stream ingest job events.

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/api/stream/projects/proj_123/ingest/job_456');
```

#### Events Sent (Server → Client)

**ingest.job.created**
```json
{
  "type": "ingest.job.created",
  "job": {
    "id": "job_456",
    "status": "QUEUED",
    "progress": 0.0
  }
}
```

**ingest.job.updated**
```json
{
  "type": "ingest.job.updated",
  "job": {
    "id": "job_456",
    "status": "RUNNING",
    "progress": 0.65,
    "stage": "CHUNKING"
  }
}
```

**ingest.job.completed**
```json
{
  "type": "ingest.job.completed",
  "job": {
    "id": "job_456",
    "status": "COMPLETED",
    "progress": 1.0
  }
}
```

**ingest.job.failed**
```json
{
  "type": "ingest.job.failed",
  "job": {
    "id": "job_456",
    "status": "FAILED"
  },
  "errorMessage": "Failed to process file: Invalid format"
}
```

#### Error Events
```json
{
  "error": "job_not_found",
  "job_id": "job_456"
}
```

---

### WebSocket /api/stream/projects/{projectId}/agent-runs/{runId}

Stream agent run and workflow node events.

#### Events Sent (Server → Client)

**agent.run.created**
```json
{
  "type": "agent.run.created",
  "run": {
    "id": "run_123",
    "status": "PENDING"
  }
}
```

**agent.run.updated**
```json
{
  "type": "agent.run.updated",
  "run": {
    "id": "run_123",
    "status": "RUNNING",
    "outputSummary": "Processing..."
  }
}
```

**agent.run.completed**
```json
{
  "type": "agent.run.completed",
  "run": {
    "id": "run_123",
    "status": "COMPLETED",
    "outputSummary": "Analysis complete"
  }
}
```

**agent.run.failed**
```json
{
  "type": "agent.run.failed",
  "run": {
    "id": "run_123",
    "status": "FAILED"
  },
  "errorMessage": "Agent execution failed"
}
```

**agent.step.updated**
```json
{
  "type": "agent.step.updated",
  "step": {
    "id": "step_789",
    "runId": "run_123",
    "status": "COMPLETED",
    "output": "Retrieved 5 documents"
  }
}
```

**agent.message.appended**
```json
{
  "type": "agent.message.appended",
  "message": {
    "id": "msg_456",
    "role": "assistant",
    "content": "Here are the results..."
  }
}
```

**workflow.node_state.updated**
```json
{
  "type": "workflow.node_state.updated",
  "nodeState": {
    "runId": "run_123",
    "nodeId": "retrieve",
    "status": "COMPLETED",
    "progress": 1.0
  }
}
```

---

### WebSocket /api/stream/projects/{projectId}/workflows/{runId}

Stream workflow node state events.

#### Events Sent (Server → Client)

**workflow.node_state.updated**
```json
{
  "type": "workflow.node_state.updated",
  "nodeState": {
    "runId": "run_123",
    "nodeId": "retrieve",
    "status": "RUNNING",
    "progress": 0.5,
    "messages": ["Processing..."]
  }
}
```

**workflow.run.updated**
```json
{
  "type": "workflow.run.updated",
  "run": {
    "id": "run_123",
    "status": "RUNNING",
    "lastMessage": "Processing node: retrieve"
  }
}
```

---

## Server-Sent Events (SSE) Alternative

### GET /api/stream/projects/{projectId}/ingest/{jobId}/events

SSE endpoint for ingest job events.

#### Headers
```
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

#### Event Format
```
event: ingest.job.updated
data: {"type":"ingest.job.updated","job":{"id":"job_456","status":"RUNNING","progress":0.65}}

event: ingest.job.completed
data: {"type":"ingest.job.completed","job":{"id":"job_456","status":"COMPLETED","progress":1.0}}
```

---

## Connection Management

### Authentication
- WebSocket: Include token in query parameter or header
- SSE: Include token in Authorization header

### Reconnection
- Clients should implement exponential backoff
- Reconnect on connection close
- Handle connection errors gracefully

### Heartbeat
- Server sends ping every 30 seconds
- Client responds with pong
- Connection closed if no pong received

## Error Handling

### Connection Errors
```json
{
  "error": "connection_error",
  "message": "Failed to establish connection"
}
```

### Invalid Job/Run ID
```json
{
  "error": "job_not_found",
  "job_id": "job_456"
}
```

### Authentication Errors
```json
{
  "error": "authentication_required",
  "message": "Valid token required"
}
```

## Notes

- WebSocket preferred for bidirectional communication
- SSE suitable for server-to-client only
- Events are JSON-encoded strings
- Connection automatically closed on job/run completion
- Multiple clients can subscribe to same stream
- Events are idempotent (can be replayed)


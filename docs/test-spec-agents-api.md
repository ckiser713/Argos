# Test Specification: Agents API

## Purpose
Comprehensive test specification for Agents API endpoints, covering missing endpoints (get run, list steps, list messages, cancel run), agent profiles, and project-scoped operations.

## Test Cases

### 1. List Agent Runs

#### 1.1 List Runs with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/agent-runs`
- **Setup**: Create 25 agent runs
- **Action**: GET request with default pagination
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<AgentRun>`
  - Includes `items`, `nextCursor`, `total`
  - Default limit applied

#### 1.2 List Runs with Status Filter
- **Setup**: Create runs with different statuses (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- **Action**: GET request with `status=COMPLETED`
- **Expected**: 
  - Returns only runs with status `COMPLETED`
  - Other statuses excluded

#### 1.3 List Runs with Workflow Filter
- **Setup**: Create runs for different workflows
- **Action**: GET request with `workflowId={workflowId}`
- **Expected**: 
  - Returns only runs for specified workflow
  - Other workflows excluded

#### 1.4 List Runs with Combined Filters
- **Action**: GET request with `status=RUNNING&workflowId={id}`
- **Expected**: 
  - Returns runs matching ALL criteria
  - Logical AND behavior

### 2. Start Agent Run

#### 2.1 Start Run with Required Fields
- **Endpoint**: `POST /api/projects/{projectId}/agent-runs`
- **Request Body**: 
  ```json
  {
    "workflowId": "wf_123",
    "inputQuery": "Analyze the codebase structure"
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `AgentRun`
  - Run has generated `id`
  - Status set to `PENDING` or `RUNNING`
  - Timestamps set (`startedAt`)

#### 2.2 Start Run with Context Items
- **Request Body**: Includes `contextItemIds: ["ctx_1", "ctx_2"]`
- **Expected**: 
  - Context items associated with run
  - Context items accessible in run details

#### 2.3 Start Run with Invalid Workflow
- **Request Body**: `workflowId` pointing to non-existent workflow
- **Expected**: 
  - Status code: `400 Bad Request` or `404 Not Found`
  - Error message indicates invalid workflow

#### 2.4 Start Run with Invalid Context Items
- **Request Body**: `contextItemIds` containing non-existent items
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates invalid context items

#### 2.5 Start Run with Empty Query
- **Request Body**: `inputQuery: ""`
- **Expected**: 
  - Status code: `400 Bad Request` or allowed (TBD)
  - Error message if validation exists

### 3. Get Agent Run

#### 3.1 Get Existing Run
- **Endpoint**: `GET /api/projects/{projectId}/agent-runs/{runId}`
- **Setup**: Create an agent run
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete `AgentRun` object
  - Includes all fields: id, projectId, workflowId, status, inputQuery, outputSummary, startedAt, finishedAt

#### 3.2 Get Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Agent run not found"

#### 3.3 Get Run from Wrong Project
- **Setup**: Create run in project A
- **Action**: GET request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

#### 3.4 Get Run with Output Summary
- **Setup**: Create completed run with outputSummary
- **Action**: GET request
- **Expected**: 
  - Returns run with `outputSummary` populated
  - Summary contains meaningful content

### 4. List Steps for Run

#### 4.1 List Steps with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/agent-runs/{runId}/steps`
- **Setup**: Create run with 15 steps
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<AgentStep>`
  - Includes all steps for the run
  - Steps ordered by execution order (chronological)

#### 4.2 List Steps for Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 4.3 List Steps for Run with No Steps
- **Setup**: Create run that hasn't started executing
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns empty `items` array

#### 4.4 List Steps with Custom Limit
- **Action**: GET request with `limit=5`
- **Expected**: 
  - Returns exactly 5 steps (or fewer if total < 5)
  - Pagination works correctly

### 5. List Node States for Run

#### 5.1 List Node States
- **Endpoint**: `GET /api/projects/{projectId}/agent-runs/{runId}/node-states`
- **Setup**: Create run with workflow graph execution
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ items: AgentNodeState[] }`
  - Includes states for all nodes in workflow
  - States include nodeId, status, progress, messages

#### 5.2 List Node States for Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 5.3 List Node States for Run with No Execution
- **Setup**: Create run that hasn't started
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns empty `items` array

### 6. List Messages for Run

#### 6.1 List Messages with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/agent-runs/{runId}/messages`
- **Setup**: Create run with 20 messages
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<AgentMessage>`
  - Includes all messages for the run
  - Messages ordered chronologically
  - Includes both user and agent messages

#### 6.2 List Messages for Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 6.3 List Messages with Role Filter
- **Action**: GET request with `role=user` (if supported)
- **Expected**: 
  - Returns only user messages
  - Agent messages excluded

#### 6.4 List Messages with Type Filter
- **Action**: GET request with `type=assistant` (if supported)
- **Expected**: 
  - Returns only assistant messages
  - Other types excluded

### 7. Append User Message to Run

#### 7.1 Append Message to Existing Run
- **Endpoint**: `POST /api/projects/{projectId}/agent-runs/{runId}/messages`
- **Setup**: Create run with status `RUNNING` or `COMPLETED`
- **Request Body**: 
  ```json
  {
    "content": "Can you provide more details?",
    "contextItemIds": ["ctx_1"]
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `AgentMessage`
  - Message has generated `id`
  - Message type is `user`
  - Run status may change (e.g., back to `RUNNING` if was `COMPLETED`)

#### 7.2 Append Message with Context Items
- **Request Body**: Includes `contextItemIds`
- **Expected**: 
  - Context items associated with message
  - Context accessible for agent processing

#### 7.3 Append Message to Non-Existent Run
- **Action**: POST request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 7.4 Append Message to Cancelled Run
- **Setup**: Create run with status `CANCELLED`
- **Action**: POST request
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates run cannot accept messages

#### 7.5 Append Empty Message
- **Request Body**: `content: ""`
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates content required

### 8. Cancel Agent Run

#### 8.1 Cancel Running Run
- **Endpoint**: `POST /api/projects/{projectId}/agent-runs/{runId}/cancel`
- **Setup**: Create run with status `RUNNING`
- **Action**: POST request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `AgentRun` with status `CANCELLED`
  - Background execution stops (if applicable)
  - `finishedAt` timestamp set

#### 8.2 Cancel Pending Run
- **Setup**: Create run with status `PENDING`
- **Action**: POST request
- **Expected**: 
  - Status changes to `CANCELLED`
  - Run cancelled before execution starts

#### 8.3 Cancel Already Completed Run
- **Setup**: Create run with status `COMPLETED`
- **Action**: POST request
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates run cannot be cancelled
  - Status remains `COMPLETED`

#### 8.4 Cancel Already Cancelled Run
- **Setup**: Create run with status `CANCELLED`
- **Action**: POST request
- **Expected**: 
  - Status code: `400 Bad Request` or `200 OK` (idempotent)
  - Error message if not idempotent

#### 8.5 Cancel Non-Existent Run
- **Action**: POST request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

### 9. List Agent Profiles

#### 9.1 List Available Agents
- **Endpoint**: `GET /api/agents/profiles`
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `List<AgentProfile>`
  - Includes all available agent profiles
  - Each profile has id, name, description, capabilities

#### 9.2 Get Single Agent Profile
- **Endpoint**: `GET /api/agents/profiles/{agentId}`
- **Setup**: Agent profile exists
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete `AgentProfile`
  - All fields present

#### 9.3 Get Non-Existent Agent Profile
- **Action**: GET request with invalid agentId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Agent not found"

### 10. Agent Run Streaming

#### 10.1 Stream Run Events via WebSocket
- **Endpoint**: `WebSocket /api/stream/agents/{runId}`
- **Setup**: Create agent run
- **Action**: Connect WebSocket and start run
- **Expected**: 
  - Connection established
  - Receives `agent.run.created` event
  - Receives `agent.run.updated` events during execution
  - Receives `agent.step.updated` events for each step
  - Receives `agent.message.appended` events for messages
  - Receives `agent.run.completed` event on finish

#### 10.2 Stream Events for Non-Existent Run
- **Action**: Connect WebSocket with invalid runId
- **Expected**: 
  - Connection rejected or closed immediately
  - Error message sent

#### 10.3 Stream Events for Completed Run
- **Setup**: Create completed run
- **Action**: Connect WebSocket
- **Expected**: 
  - Connection established
  - Receives final state
  - No new events (or historical events TBD)

## Test Data

### Sample AgentRun
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

### Sample AgentStep
```json
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
```

### Sample AgentMessage
```json
{
  "id": "msg_456",
  "runId": "run_123",
  "role": "user",
  "content": "Can you provide more details?",
  "contextItemIds": ["ctx_1"],
  "createdAt": "2024-01-15T10:05:00Z"
}
```

### Sample AgentNodeState
```json
{
  "runId": "run_123",
  "nodeId": "retrieve_docs",
  "status": "COMPLETED",
  "progress": 1.0,
  "messages": ["Retrieved documents successfully"],
  "startedAt": "2024-01-15T10:00:05Z",
  "completedAt": "2024-01-15T10:00:06Z"
}
```

## Edge Cases

1. **Very Long Runs**: Runs with 1000+ steps
2. **Very Long Messages**: Messages with content > 100KB
3. **Concurrent Cancellations**: Multiple cancel requests for same run
4. **Race Conditions**: Starting run while cancelling
5. **Invalid Workflow States**: Runs referencing deleted workflows
6. **Message Ordering**: Ensuring chronological order
7. **Step Ordering**: Ensuring execution order
8. **WebSocket Disconnections**: Handling client disconnects gracefully

## Dependencies

- FastAPI TestClient
- WebSocket test client
- Database fixtures (projects, workflows, context items)
- Mock agent service (for unit tests)
- Background task mocking (for execution tests)

## Test Implementation Notes

- Use pytest fixtures for run setup
- Mock background tasks to avoid actual execution
- Use WebSocket test client for streaming tests
- Test both unit (service layer) and integration (API layer) levels
- Verify database state changes, not just HTTP responses
- Test concurrent operations for race conditions
- Use transaction rollback for data cleanup
- Mock LangGraph execution for run tests


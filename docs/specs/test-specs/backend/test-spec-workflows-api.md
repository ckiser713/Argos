# Test Specification: Workflows API

## Purpose
Comprehensive test specification for Workflows API endpoints, covering workflow execution, node state management, graph operations, and project-scoped operations.

## Test Cases

### 1. List Workflow Graphs

#### 1.1 List Available Graphs
- **Endpoint**: `GET /api/workflows/graphs`
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `List<WorkflowGraph>`
  - Includes all available workflow graphs
  - Each graph has id, name, description, nodes, edges

#### 1.2 List Graphs for Project
- **Endpoint**: `GET /api/projects/{projectId}/workflows/graphs` (if project-scoped)
- **Action**: GET request
- **Expected**: 
  - Returns graphs available for the project
  - May include project-specific custom graphs

### 2. Get Workflow Graph

#### 2.1 Get Existing Graph
- **Endpoint**: `GET /api/workflows/graphs/{workflowId}`
- **Setup**: Workflow graph exists
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete `WorkflowGraph`
  - Includes all nodes and edges
  - Graph structure is valid

#### 2.2 Get Non-Existent Graph
- **Action**: GET request with invalid workflowId
- **Expected**: 
  - Status code: `404 Not Found`
  - Error message: "Workflow not found"

#### 2.3 Get Graph with Node Positions
- **Expected**: 
  - Nodes include x, y coordinates (if applicable)
  - Positions usable for UI rendering

### 3. List Workflow Runs

#### 3.1 List Runs with Pagination
- **Endpoint**: `GET /api/projects/{projectId}/workflows/runs`
- **Setup**: Create 25 workflow runs
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `PaginatedResponse<WorkflowRun>`
  - Includes pagination metadata

#### 3.2 List Runs with Status Filter
- **Setup**: Create runs with different statuses
- **Action**: GET request with `status=RUNNING`
- **Expected**: 
  - Returns only runs with specified status
  - Other statuses excluded

#### 3.3 List Runs with Workflow Filter
- **Action**: GET request with `workflowId={workflowId}`
- **Expected**: 
  - Returns only runs for specified workflow
  - Other workflows excluded

### 4. Create Workflow Run

#### 4.1 Start Run with Valid Graph
- **Endpoint**: `POST /api/projects/{projectId}/workflows/runs`
- **Setup**: Workflow graph exists
- **Request Body**: 
  ```json
  {
    "workflowId": "wf_123",
    "input": { "query": "Analyze codebase" }
  }
  ```
- **Expected**: 
  - Status code: `201 Created`
  - Returns created `WorkflowRun`
  - Run has generated `id`
  - Status set to `PENDING` or `RUNNING`
  - Timestamps set

#### 4.2 Start Run with Invalid Graph
- **Request Body**: `workflowId` pointing to non-existent graph
- **Expected**: 
  - Status code: `400 Bad Request` or `404 Not Found`
  - Error message indicates invalid workflow

#### 4.3 Start Run with Input Parameters
- **Request Body**: Includes workflow-specific input parameters
- **Expected**: 
  - Input stored correctly
  - Input accessible during execution

#### 4.4 Start Run with Context
- **Request Body**: Includes `contextItemIds`
- **Expected**: 
  - Context associated with run
  - Context accessible during execution

### 5. Get Workflow Run

#### 5.1 Get Existing Run
- **Endpoint**: `GET /api/projects/{projectId}/workflows/runs/{runId}`
- **Setup**: Create workflow run
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns complete `WorkflowRun`
  - Includes all fields: id, projectId, workflowId, status, input, output, startedAt, finishedAt

#### 5.2 Get Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 5.3 Get Run from Wrong Project
- **Setup**: Create run in project A
- **Action**: GET request with project B's ID
- **Expected**: 
  - Status code: `404 Not Found`

### 6. Get Node States for Run

#### 6.1 List Node States
- **Endpoint**: `GET /api/projects/{projectId}/workflows/runs/{runId}/node-states`
- **Setup**: Create run with workflow execution
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `{ items: WorkflowNodeState[] }`
  - Includes states for all nodes in workflow
  - States include nodeId, status, progress, messages

#### 6.2 List Node States for Non-Existent Run
- **Action**: GET request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

#### 6.3 List Node States for Pending Run
- **Setup**: Create run that hasn't started
- **Action**: GET request
- **Expected**: 
  - Status code: `200 OK`
  - Returns empty `items` array or initial states

#### 6.4 List Node States with Status Filter
- **Action**: GET request with `status=RUNNING` (if supported)
- **Expected**: 
  - Returns only nodes with specified status
  - Other statuses excluded

### 7. Update Node State

#### 7.1 Update Node Status
- **Endpoint**: `PATCH /api/projects/{projectId}/workflows/runs/{runId}/nodes/{nodeId}` (if exists)
- **Setup**: Create run with node execution
- **Request Body**: `{ status: "COMPLETED", progress: 1.0 }`
- **Expected**: 
  - Status code: `200 OK`
  - Node state updated
  - Progress updated
  - Change reflected in run state

#### 7.2 Update Node Progress
- **Request Body**: `{ progress: 0.75 }`
- **Expected**: 
  - Progress updated
  - Status may change (e.g., to RUNNING if was PENDING)

#### 7.3 Update Node with Messages
- **Request Body**: `{ messages: ["Processing step 1", "Processing step 2"] }`
- **Expected**: 
  - Messages appended or replaced (TBD)
  - Messages accessible in node state

#### 7.4 Update Non-Existent Node
- **Action**: PATCH request with invalid nodeId
- **Expected**: 
  - Status code: `404 Not Found`

### 8. Cancel Workflow Run

#### 8.1 Cancel Running Run
- **Endpoint**: `POST /api/projects/{projectId}/workflows/runs/{runId}/cancel`
- **Setup**: Create run with status `RUNNING`
- **Action**: POST request
- **Expected**: 
  - Status code: `200 OK`
  - Returns `WorkflowRun` with status `CANCELLED`
  - Background execution stops
  - `finishedAt` timestamp set
  - All node states updated to `CANCELLED`

#### 8.2 Cancel Pending Run
- **Setup**: Create run with status `PENDING`
- **Action**: POST request
- **Expected**: 
  - Status changes to `CANCELLED`
  - Run cancelled before execution starts

#### 8.3 Cancel Completed Run
- **Setup**: Create run with status `COMPLETED`
- **Action**: POST request
- **Expected**: 
  - Status code: `400 Bad Request` or `409 Conflict`
  - Error message indicates run cannot be cancelled
  - Status remains `COMPLETED`

#### 8.4 Cancel Non-Existent Run
- **Action**: POST request with invalid runId
- **Expected**: 
  - Status code: `404 Not Found`

### 9. Workflow Execution

#### 9.1 Execute Workflow Successfully
- **Setup**: Create workflow graph and start run
- **Action**: Monitor execution
- **Expected**: 
  - Run progresses through nodes in correct order
  - Node states update correctly
  - Final status is `COMPLETED`
  - Output generated

#### 9.2 Handle Workflow Failure
- **Setup**: Create workflow that will fail at a node
- **Action**: Monitor execution
- **Expected**: 
  - Run status changes to `FAILED`
  - Error message captured
  - Failed node state includes error details
  - Subsequent nodes not executed

#### 9.3 Handle Workflow Timeout
- **Setup**: Create long-running workflow
- **Action**: Timeout occurs
- **Expected**: 
  - Run status changes to `FAILED` or `TIMEOUT`
  - Timeout error captured
  - Partial results preserved

#### 9.4 Execute Workflow with Conditional Branches
- **Setup**: Create workflow with conditional logic
- **Action**: Execute with different inputs
- **Expected**: 
  - Correct branch taken based on input
  - Unused branches not executed
  - Graph structure respected

### 10. Workflow Streaming

#### 10.1 Stream Workflow Events via WebSocket
- **Endpoint**: `WebSocket /api/stream/workflows/{runId}`
- **Setup**: Create workflow run
- **Action**: Connect WebSocket and start run
- **Expected**: 
  - Connection established
  - Receives `workflow.run.created` event
  - Receives `workflow.node_state.updated` events for each node
  - Receives `workflow.run.completed` event on finish

#### 10.2 Stream Node State Updates
- **Expected**: 
  - Receives updates when node status changes
  - Receives updates when node progress changes
  - Updates include complete node state

#### 10.3 Stream Events for Non-Existent Run
- **Action**: Connect WebSocket with invalid runId
- **Expected**: 
  - Connection rejected or closed immediately
  - Error message sent

### 11. Workflow Graph Validation

#### 11.1 Validate Graph Structure
- **Setup**: Create workflow graph
- **Action**: Validate graph
- **Expected**: 
  - Graph structure is valid
  - All nodes have valid IDs
  - All edges reference existing nodes
  - Graph is acyclic (if required)

#### 11.2 Detect Invalid Graph
- **Setup**: Create graph with invalid structure
- **Action**: Attempt to use graph
- **Expected**: 
  - Status code: `400 Bad Request`
  - Error message indicates graph validation failure

#### 11.3 Validate Node Types
- **Expected**: 
  - Start nodes exist
  - End nodes exist
  - Node types are valid
  - Required node properties present

## Test Data

### Sample WorkflowGraph
```json
{
  "id": "wf_123",
  "name": "Default Retrieval Workflow",
  "description": "Start -> retrieve_docs -> grade_documents -> generate_answer -> end",
  "nodes": [
    {
      "id": "start",
      "label": "__start__",
      "type": "start",
      "x": 250,
      "y": 0
    },
    {
      "id": "retrieve",
      "label": "retrieve_docs",
      "type": "tool",
      "x": 250,
      "y": 100
    },
    {
      "id": "grade",
      "label": "grade_documents",
      "type": "tool",
      "x": 250,
      "y": 200
    },
    {
      "id": "generate",
      "label": "generate_answer",
      "type": "llm",
      "x": 250,
      "y": 300
    },
    {
      "id": "end",
      "label": "__end__",
      "type": "end",
      "x": 250,
      "y": 400
    }
  ],
  "edges": [
    {
      "id": "e1",
      "source": "start",
      "target": "retrieve"
    },
    {
      "id": "e2",
      "source": "retrieve",
      "target": "grade"
    },
    {
      "id": "e3",
      "source": "grade",
      "target": "generate"
    },
    {
      "id": "e4",
      "source": "generate",
      "target": "end"
    }
  ]
}
```

### Sample WorkflowRun
```json
{
  "id": "run_123",
  "projectId": "proj_abc",
  "workflowId": "wf_456",
  "status": "RUNNING",
  "input": {
    "query": "Analyze the codebase"
  },
  "output": null,
  "startedAt": "2024-01-15T10:00:00Z",
  "finishedAt": null,
  "lastMessage": "Processing node: retrieve_docs"
}
```

### Sample WorkflowNodeState
```json
{
  "runId": "run_123",
  "nodeId": "retrieve",
  "status": "COMPLETED",
  "progress": 1.0,
  "messages": [
    "Retrieved 5 documents",
    "Filtered to 3 relevant documents"
  ],
  "startedAt": "2024-01-15T10:00:05Z",
  "completedAt": "2024-01-15T10:00:10Z",
  "error": null
}
```

## Edge Cases

1. **Very Large Workflows**: Graphs with 100+ nodes
2. **Deep Workflows**: Chains of 50+ nodes
3. **Wide Workflows**: Nodes with 20+ outgoing edges
4. **Concurrent Executions**: Multiple runs of same workflow
5. **Long-Running Workflows**: Runs taking hours
6. **Workflow Failures**: Handling errors gracefully
7. **Node Timeouts**: Individual nodes timing out
8. **Invalid Inputs**: Workflows receiving invalid input data

## Dependencies

- FastAPI TestClient
- WebSocket test client
- Database fixtures (projects, workflows, runs)
- Mock workflow service (for unit tests)
- LangGraph mocking (for execution tests)
- Background task mocking

## Test Implementation Notes

- Use pytest fixtures for workflow setup
- Mock LangGraph execution to avoid actual model calls
- Use WebSocket test client for streaming tests
- Test both unit (service layer) and integration (API layer) levels
- Verify database state changes
- Test concurrent executions for race conditions
- Use transaction rollback for data cleanup
- Test graph validation logic
- Mock external services (LLM, tools)


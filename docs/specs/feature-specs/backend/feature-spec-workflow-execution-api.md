# Feature Specification: Workflow Execution API

## Overview

Implementation specification for workflow execution API endpoints, including execute, cancel, pause/resume operations, and execution state management.

## Current State

- Basic workflow run creation exists (`POST /api/projects/{projectId}/workflows/runs`)
- Workflow runs are created but not actually executed
- No cancel, pause, or resume endpoints
- Execution state tracking incomplete
- No background task execution

## Target State

- Complete workflow execution API
- Background task execution with LangGraph
- Cancel, pause, and resume operations
- Execution state tracking
- Real-time execution updates via WebSocket

## Requirements

### Functional Requirements

1. Execute workflow run (start background execution)
2. Cancel running workflow
3. Pause workflow execution (checkpoint state)
4. Resume paused workflow
5. Get execution status and progress
6. List execution history
7. Handle execution errors gracefully

### Non-Functional Requirements

1. Background execution with async tasks
2. State persistence for pause/resume
3. Efficient cancellation (< 1 second)
4. Support long-running workflows (hours/days)
5. Resource cleanup on cancellation

## Technical Design

### Endpoints

#### POST /api/projects/{projectId}/workflows/runs/{runId}/execute

Start execution of a workflow run.

**Request Body**: (optional)

```json
{
  "input_data": {
    "query": "What is the status of project X?",
    "context": {}
  }
}
```

**Response**: 202 Accepted

```json
{
  "run_id": "run_123",
  "status": "RUNNING",
  "started_at": "2024-01-15T10:00:00Z",
  "message": "Workflow execution started"
}
```

**Error Responses**:
- 404: Run not found
- 400: Run already executing or invalid state
- 409: Run already completed

#### POST /api/projects/{projectId}/workflows/runs/{runId}/cancel

Cancel a running workflow.

**Response**: 200 OK

```json
{
  "run_id": "run_123",
  "status": "CANCELLED",
  "cancelled_at": "2024-01-15T10:30:00Z",
  "message": "Workflow execution cancelled"
}
```

**Error Responses**:
- 404: Run not found
- 400: Run cannot be cancelled (already completed/failed)

#### POST /api/projects/{projectId}/workflows/runs/{runId}/pause

Pause a running workflow (checkpoint state).

**Response**: 200 OK

```json
{
  "run_id": "run_123",
  "status": "PAUSED",
  "paused_at": "2024-01-15T10:30:00Z",
  "checkpoint_id": "checkpoint_456",
  "message": "Workflow paused at checkpoint"
}
```

**Error Responses**:
- 404: Run not found
- 400: Run cannot be paused (not running)

#### POST /api/projects/{projectId}/workflows/runs/{runId}/resume

Resume a paused workflow from checkpoint.

**Request Body**: (optional)

```json
{
  "checkpoint_id": "checkpoint_456"
}
```

**Response**: 202 Accepted

```json
{
  "run_id": "run_123",
  "status": "RUNNING",
  "resumed_at": "2024-01-15T11:00:00Z",
  "message": "Workflow resumed from checkpoint"
}
```

**Error Responses**:
- 404: Run not found
- 400: Run cannot be resumed (not paused)

#### GET /api/projects/{projectId}/workflows/runs/{runId}/status

Get current execution status and progress.

**Response**: 200 OK

```json
{
  "run_id": "run_123",
  "status": "RUNNING",
  "progress": 0.65,
  "current_node": "node_generate",
  "started_at": "2024-01-15T10:00:00Z",
  "estimated_completion": "2024-01-15T10:45:00Z",
  "node_states": [
    {
      "node_id": "node_retrieve",
      "status": "COMPLETED",
      "progress": 1.0,
      "completed_at": "2024-01-15T10:05:00Z"
    },
    {
      "node_id": "node_generate",
      "status": "RUNNING",
      "progress": 0.65,
      "started_at": "2024-01-15T10:10:00Z"
    }
  ]
}
```

### Background Execution

#### Task Queue Integration

- Use Celery or similar for background task execution
- Store task IDs in workflow_runs table
- Handle task failures and retries

#### LangGraph Execution

```python
async def execute_workflow_task(run_id: str, workflow_id: str, input_data: dict):
    workflow = workflow_service.get_graph(workflow_id)
    compiled_graph = compile_langgraph_workflow(workflow)
    
    # Update run status
    workflow_service.update_run_status(run_id, WorkflowRunStatus.RUNNING)
    
    try:
        # Stream execution events
        async for event in compiled_graph.astream_events(input_data, version="v1"):
            # Update node states
            if event["event"] == "on_chain_start":
                node_id = event["name"]
                workflow_service.set_node_state(
                    run_id, node_id,
                    status=WorkflowNodeStatus.RUNNING,
                    progress=0.0,
                    started=True
                )
            
            elif event["event"] == "on_chain_end":
                node_id = event["name"]
                workflow_service.set_node_state(
                    run_id, node_id,
                    status=WorkflowNodeStatus.COMPLETED,
                    progress=1.0,
                    completed=True
                )
            
            # Emit WebSocket event
            emit_workflow_event(run_id, event)
        
        # Mark as completed
        workflow_service.update_run_status(
            run_id,
            WorkflowRunStatus.COMPLETED,
            finished=True,
            output_data=event.get("data", {})
        )
    
    except CancelledError:
        workflow_service.update_run_status(run_id, WorkflowRunStatus.CANCELLED, finished=True)
    except Exception as e:
        workflow_service.update_run_status(
            run_id,
            WorkflowRunStatus.FAILED,
            finished=True,
            last_message=f"Execution failed: {str(e)}"
        )
```

### State Management

#### Checkpoint System

- Store workflow state at pause points
- Serialize LangGraph state to JSON
- Store in `workflow_runs.checkpoint_json` field
- Restore state on resume

#### Cancellation

- Use cancellation tokens
- Clean up resources (connections, file handles)
- Update all node states to CANCELLED
- Emit cancellation events

### Database Schema Updates

```sql
ALTER TABLE workflow_runs ADD COLUMN task_id TEXT;
ALTER TABLE workflow_runs ADD COLUMN checkpoint_json TEXT;
ALTER TABLE workflow_runs ADD COLUMN paused_at TEXT;
ALTER TABLE workflow_runs ADD COLUMN cancelled_at TEXT;
ALTER TABLE workflow_runs ADD COLUMN estimated_completion TEXT;
CREATE INDEX idx_workflow_runs_task_id ON workflow_runs(task_id);
```

## Implementation Steps

1. Add execution endpoints to `workflows.py` router
2. Implement background task execution (Celery/async)
3. Integrate LangGraph execution in workflow service
4. Add checkpoint/pause/resume logic
5. Add cancellation handling
6. Update database schema
7. Add WebSocket event emission
8. Write tests
9. Add error handling and recovery

## Testing Strategy

### Unit Tests

- Test execution endpoint handlers
- Test cancellation logic
- Test pause/resume checkpoint system
- Test state updates

### Integration Tests

- Test with LangGraph workflows
- Test background task execution
- Test cancellation during execution
- Test pause/resume flow
- Test error recovery

### Performance Tests

- Test long-running workflows
- Test cancellation response time
- Test checkpoint serialization performance

## Success Criteria

1. All execution endpoints work correctly
2. Background execution works
3. Cancel works within 1 second
4. Pause/resume works correctly
5. State persistence works
6. Real-time updates work
7. Tests pass
8. Error handling works

## Notes

- Consider using Redis for task queue
- Implement workflow timeouts
- Add execution metrics and monitoring
- Consider workflow versioning for resume compatibility
- Optimize checkpoint serialization size


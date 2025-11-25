# Feature Specification: Real-Time Event Integration

## Overview

Implementation specification for connecting backend services to the WebSocket streaming infrastructure, ensuring real-time updates for ingest jobs, agent runs, and workflow execution.

## Current State

- WebSocket endpoints exist (`/api/stream/projects/{projectId}/ingest/{jobId}`, `/api/stream/projects/{projectId}/agent-runs/{runId}`, `/api/stream/projects/{projectId}/workflows/runs/{runId}`)
- `ConnectionManager` and `StreamingService` implemented
- Services (`IngestService`, `AgentService`, `WorkflowService`) do not emit events
- No real-time updates during job processing
- Frontend not receiving live updates

## Target State

- All long-running operations emit real-time events
- Services integrated with streaming service
- Frontend receives live updates for all operations
- Event-driven architecture fully functional
- Efficient event distribution

## Requirements

### Functional Requirements

1. Ingest jobs emit events during processing
2. Agent runs emit step-by-step events
3. Workflow nodes emit state updates
4. Events broadcast to all connected clients
5. Event filtering by project
6. Connection management (reconnect handling)

### Non-Functional Requirements

1. Low latency (< 100ms event delivery)
2. Support 100+ concurrent connections
3. Efficient event distribution
4. Graceful degradation if WebSocket unavailable
5. Event ordering guarantees

## Technical Design

### Service Integration

#### IngestService Integration

```python
from app.services.streaming_service import emit_ingest_event

class IngestService:
    def process_job(self, job_id: str):
        # Emit job created event
        emit_ingest_event(job.project_id, "ingest.job.created", job)
        
        try:
            # Update stage
            self._update_stage(job_id, "PREPROCESSING")
            emit_ingest_event(job.project_id, "ingest.job.updated", job)
            
            # Process...
            self._update_progress(job_id, 0.5)
            emit_ingest_event(job.project_id, "ingest.job.updated", job)
            
            # Complete
            self._complete_job(job_id)
            emit_ingest_event(job.project_id, "ingest.job.completed", job)
        except Exception as e:
            self._fail_job(job_id, str(e))
            emit_ingest_event(job.project_id, "ingest.job.failed", job, error=str(e))
```

#### AgentService Integration

```python
from app.services.streaming_service import emit_agent_event

class AgentService:
    async def execute_run(self, run_id: str):
        run = self.get_run(run_id)
        emit_agent_event(run.project_id, "agent.run.created", run)
        
        try:
            # Execute steps
            for step in self._execute_steps(run):
                self._save_step(step)
                emit_agent_event(run.project_id, "agent.step.updated", step)
                
                # Update node states
                for node_state in step.node_states:
                    emit_agent_event(run.project_id, "workflow.node_state.updated", node_state)
            
            # Complete
            self._complete_run(run_id)
            emit_agent_event(run.project_id, "agent.run.completed", run)
        except Exception as e:
            self._fail_run(run_id, str(e))
            emit_agent_event(run.project_id, "agent.run.failed", run, error=str(e))
```

#### WorkflowService Integration

```python
from app.services.streaming_service import emit_workflow_event

class WorkflowService:
    async def execute_workflow(self, workflow_id: str, input_data: dict):
        run = self.create_run(workflow_id, input_data)
        emit_workflow_event(run.project_id, "workflow.run.created", run)
        
        async for event in langgraph_workflow.astream_events(input_data, version="v1"):
            # Update node state
            node_state = self._update_node_state(run.id, event)
            emit_workflow_event(run.project_id, "workflow.node_state.updated", node_state)
        
        # Complete
        self._complete_run(run.id)
        emit_workflow_event(run.project_id, "workflow.run.completed", run)
```

### Event Types

#### Ingest Events

- `ingest.job.created` - Job created
- `ingest.job.updated` - Progress/stage update
- `ingest.job.completed` - Job completed successfully
- `ingest.job.failed` - Job failed with error
- `ingest.job.cancelled` - Job cancelled

#### Agent Events

- `agent.run.created` - Run started
- `agent.run.updated` - Run status/progress update
- `agent.run.completed` - Run completed
- `agent.run.failed` - Run failed
- `agent.run.cancelled` - Run cancelled
- `agent.step.updated` - Step execution update
- `agent.message.appended` - New message added

#### Workflow Events

- `workflow.run.created` - Workflow run started
- `workflow.run.updated` - Run status update
- `workflow.run.completed` - Run completed
- `workflow.run.failed` - Run failed
- `workflow.run.cancelled` - Run cancelled
- `workflow.node.started` - Node execution started
- `workflow.node.completed` - Node execution completed
- `workflow.node.failed` - Node execution failed
- `workflow.node_state.updated` - Node state changed

### StreamingService Enhancements

```python
class StreamingService:
    def emit_ingest_event(self, project_id: str, event_type: str, job: IngestJob, error: Optional[str] = None):
        event = {
            "type": event_type,
            "job": job.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if error:
            event["errorMessage"] = error
        asyncio.create_task(self.connection_manager.broadcast(project_id, event))
    
    def emit_agent_event(self, project_id: str, event_type: str, data: Union[AgentRun, AgentStep, AgentNodeState], error: Optional[str] = None):
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if isinstance(data, AgentRun):
            event["run"] = data.model_dump()
        elif isinstance(data, AgentStep):
            event["step"] = data.model_dump()
        elif isinstance(data, AgentNodeState):
            event["nodeState"] = data.model_dump()
        
        if error:
            event["errorMessage"] = error
        
        asyncio.create_task(self.connection_manager.broadcast(project_id, event))
    
    def emit_workflow_event(self, project_id: str, event_type: str, data: Union[WorkflowRun, dict], error: Optional[str] = None):
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if isinstance(data, WorkflowRun):
            event["run"] = data.model_dump()
        elif isinstance(data, dict):
            # Handle node state updates and other dict-based events
            event.update(data)
        
        if error:
            event["errorMessage"] = error
        
        asyncio.create_task(self.connection_manager.broadcast(project_id, event))
```

## Implementation Steps

1. **Update StreamingService**
   - Add helper methods for each event type
   - Ensure async event broadcasting
   - Add error handling

2. **Integrate IngestService**
   - Add event emissions at key points
   - Emit progress updates
   - Emit stage transitions

3. **Integrate AgentService**
   - Add event emissions for steps
   - Emit node state updates
   - Emit message events

4. **Integrate WorkflowService**
   - Connect to LangGraph event stream
   - Emit node state updates
   - Emit run completion events

5. **Add Error Handling**
   - Graceful degradation if WebSocket unavailable
   - Retry logic for failed broadcasts
   - Logging for debugging

6. **Testing**
   - Unit tests for event emission
   - Integration tests for WebSocket delivery
   - Load tests for concurrent connections

## Testing Strategy

### Unit Tests

- Test event emission from services
- Test event payload structure
- Test error handling

### Integration Tests

- Test WebSocket connection
- Test event delivery to clients
- Test multiple concurrent connections
- Test reconnection handling

### Load Tests

- Test 100+ concurrent connections
- Test event throughput
- Test memory usage

## Success Criteria

1. All services emit events correctly
2. Events delivered to connected clients
3. Low latency (< 100ms)
4. Support 100+ concurrent connections
5. Graceful error handling
6. Comprehensive test coverage

## Notes

- Consider using Redis pub/sub for distributed event distribution
- Add event batching for high-frequency updates
- Consider event filtering/subscription mechanism
- Add metrics for event delivery rates


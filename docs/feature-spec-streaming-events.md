# Feature Specification: Real-Time Event Streaming

## Overview
Implementation specification for real-time event streaming via WebSocket/SSE for ingest jobs, agent runs, and workflow execution.

## Current State
- Basic WebSocket endpoints exist (stubbed)
- Streaming service implemented but uses mock data
- No real-time updates from actual operations
- Frontend not fully integrated

## Target State
- Real-time updates for all long-running operations
- WebSocket/SSE working correctly
- Event-driven architecture
- Frontend receiving real-time updates
- Efficient event distribution

## Requirements

### Functional Requirements
1. Stream ingest job events
2. Stream agent run events
3. Stream workflow node events
4. Support multiple clients
5. Handle reconnections
6. Event filtering by project

### Non-Functional Requirements
1. Low latency (< 100ms)
2. Support 100+ concurrent connections
3. Efficient event distribution
4. Connection management

## Technical Design

### Event Types

#### Ingest Job Events
- `ingest.job.created`
- `ingest.job.updated`
- `ingest.job.completed`
- `ingest.job.failed`

#### Agent Run Events
- `agent.run.created`
- `agent.run.updated`
- `agent.run.completed`
- `agent.run.failed`
- `agent.step.updated`
- `agent.message.appended`

#### Workflow Events
- `workflow.node_state.updated`
- `workflow.run.updated`

### WebSocket Implementation

#### Connection Management
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, project_id: str):
        self.active_connections[project_id].remove(websocket)
    
    async def broadcast(self, project_id: str, event: dict):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                await connection.send_json(event)
```

#### Event Emission
```python
async def emit_ingest_event(project_id: str, event_type: str, job: IngestJob):
    event = {
        "type": event_type,
        "job": job.model_dump()
    }
    await connection_manager.broadcast(project_id, event)
```

### Integration Points

#### 1. Ingest Service
- Emit events on job updates
- Emit progress updates
- Emit completion events

#### 2. Agent Service
- Emit run events
- Emit step events
- Emit message events

#### 3. Workflow Service
- Emit node state events
- Emit run events

### Frontend Integration

#### WebSocket Hook
```typescript
export function useIngestStream(projectId: string, jobId: string) {
  const [events, setEvents] = useState<IngestJobEvent[]>([]);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/stream/projects/${projectId}/ingest/${jobId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [...prev, data]);
    };
    
    return () => ws.close();
  }, [projectId, jobId]);
  
  return events;
}
```

## Testing Strategy

### Unit Tests
- Test event emission
- Test connection management
- Test event filtering

### Integration Tests
- Test WebSocket connections
- Test event delivery
- Test reconnection

## Implementation Steps

1. Implement connection manager
2. Integrate with services
3. Add event emission points
4. Update WebSocket endpoints
5. Update frontend hooks
6. Write tests
7. Load testing

## Success Criteria

1. Real-time updates work
2. Multiple clients supported
3. Reconnection works
4. Events delivered correctly
5. Performance acceptable
6. Tests pass

## Notes

- Consider Redis for distributed events
- Optimize event payload size
- Handle connection failures gracefully
- Consider event batching


# Feature Specification: Agent Run Details Endpoints

## Overview
Implementation specification for agent run details endpoints, including steps, messages, node states, and cancel operations.

## Current State
- Basic agent run endpoints exist
- Missing: get run, list steps, list messages, list node states, cancel run
- Frontend needs these endpoints for Deep Research

## Target State
- Complete agent run details API
- Steps endpoint for execution history
- Messages endpoint for conversation
- Node states endpoint for workflow visualization
- Cancel endpoint for stopping runs

## Requirements

### Functional Requirements
1. Get single agent run by ID
2. List steps for agent run (paginated)
3. List messages for agent run (paginated)
4. List node states for agent run
5. Append message to agent run
6. Cancel agent run

### Non-Functional Requirements
1. Pagination for steps/messages
2. Real-time updates via WebSocket
3. Efficient querying with indexes

## Technical Design

### Endpoints

#### GET /api/projects/{projectId}/agent-runs/{runId}
- Returns complete run details
- Includes status, input, output, timestamps

#### GET /api/projects/{projectId}/agent-runs/{runId}/steps
- Returns paginated list of steps
- Ordered by stepNumber
- Includes input, output, duration

#### GET /api/projects/{projectId}/agent-runs/{runId}/messages
- Returns paginated list of messages
- Ordered by createdAt
- Includes role, content, context

#### GET /api/projects/{projectId}/agent-runs/{runId}/node-states
- Returns all node states for run
- Includes status, progress, messages

#### POST /api/projects/{projectId}/agent-runs/{runId}/messages
- Appends user message
- May restart run if completed
- Returns created message

#### POST /api/projects/{projectId}/agent-runs/{runId}/cancel
- Cancels running run
- Updates status to CANCELLED
- Stops background execution

### Database Schema
- Use existing `agent_runs` table
- Add `agent_steps` table
- Add `agent_messages` table
- Add `agent_node_states` table

### Implementation

#### 1. Repository Layer
- Implement queries for steps, messages, node states
- Add pagination support
- Add filtering support

#### 2. Service Layer
- Implement business logic
- Handle status transitions
- Handle cancellation

#### 3. API Layer
- Implement endpoints
- Add validation
- Add error handling

### Frontend Changes
- Create hooks for new endpoints
- Update DeepResearch component
- Add real-time updates

## Testing Strategy

### Unit Tests
- Test endpoint handlers
- Test service methods
- Test repository queries

### Integration Tests
- Test with database
- Test pagination
- Test real-time updates

## Implementation Steps

1. Design database schema
2. Implement repository layer
3. Implement service layer
4. Implement API routes
5. Write tests
6. Update frontend

## Success Criteria

1. All endpoints work correctly
2. Pagination works
3. Real-time updates work
4. Cancel works correctly
5. Tests pass

## Notes

- Consider streaming for large message lists
- Optimize queries with indexes
- Cache frequently accessed data


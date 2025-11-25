# Test Specification: Workflow Service Database Persistence Migration

## Purpose
Test specification for migrating WorkflowService from in-memory storage to database persistence, including workflow graphs, runs, and node state management.

## Current State
- `WorkflowService` uses in-memory `Dict[str, WorkflowGraph]` and `Dict[str, WorkflowRun]`
- Node states stored in `Dict[str, Dict[str, WorkflowNodeState]]`
- No persistence across service restarts
- No project-scoped operations

## Target State
- Database-backed persistence
- Project-scoped workflows and runs
- Persistent node states
- Support for workflow versioning (optional)
- Transaction support

## Test Cases

### 1. Database Schema Migration

#### 1.1 Create Workflow Graphs Table
- **Action**: Run migration script
- **Expected**: 
  - Table `workflow_graphs` created
  - Columns: id, project_id, name, description, graph_json, created_at, updated_at
  - Indexes on project_id
  - JSON column for graph structure

#### 1.2 Create Workflow Runs Table
- **Action**: Run migration script
- **Expected**: 
  - Table `workflow_runs` created
  - Columns: id, project_id, workflow_id, status, input_json, output_json, started_at, finished_at, last_message
  - Indexes on project_id, workflow_id, status
  - Foreign keys on project_id, workflow_id

#### 1.3 Create Workflow Node States Table
- **Action**: Run migration script
- **Expected**: 
  - Table `workflow_node_states` created
  - Columns: run_id, node_id, status, progress, messages_json, started_at, completed_at, error
  - Composite primary key (run_id, node_id)
  - Indexes on run_id, status
  - Foreign key on run_id

#### 1.4 Migrate Existing In-Memory Data
- **Setup**: Service has in-memory graphs and runs
- **Action**: Run migration script
- **Expected**: 
  - All graphs persisted to database
  - All runs persisted to database
  - All node states persisted
  - Data integrity maintained

### 2. Workflow Graph Operations with Database

#### 2.1 Create Graph Persists to Database
- **Setup**: Fresh database
- **Action**: Call `create_graph(graph)`
- **Expected**: 
  - Graph saved to database
  - Graph retrievable via `get_graph()`
  - JSON structure preserved

#### 2.2 List Graphs Filtered by Project
- **Setup**: Create graphs in project A and project B
- **Action**: Call `list_graphs(project_id="proj_a")`
- **Expected**: 
  - Returns only graphs from project A
  - Project B graphs excluded

#### 2.3 Get Graph from Database
- **Setup**: Create graph in database
- **Action**: Call `get_graph(graph_id)`
- **Expected**: 
  - Returns graph from database
  - JSON structure deserialized correctly
  - All fields populated

#### 2.4 Update Graph Persists Changes
- **Setup**: Create graph in database
- **Action**: Call `update_graph(graph_id, updates)`
- **Expected**: 
  - Changes saved to database
  - `updated_at` timestamp updated
  - Graph structure updated

#### 2.5 Delete Graph Removes from Database
- **Setup**: Create graph in database
- **Action**: Call `delete_graph(graph_id)`
- **Expected**: 
  - Graph removed from database
  - Related runs handled (cascade or prevent TBD)

### 3. Workflow Run Operations with Database

#### 3.1 Create Run Persists to Database
- **Setup**: Workflow graph exists
- **Action**: Call `create_run(workflow_id, input)`
- **Expected**: 
  - Run saved to database
  - Run retrievable via `get_run()`
  - Initial node states created

#### 3.2 Create Run with Project ID
- **Request**: Includes `projectId`
- **Expected**: 
  - `project_id` stored correctly
  - Run queryable by project

#### 3.3 List Runs Filtered by Project
- **Setup**: Create runs in project A and project B
- **Action**: Call `list_runs(project_id="proj_a")`
- **Expected**: 
  - Returns only runs from project A
  - Project B runs excluded

#### 3.4 List Runs Filtered by Status
- **Setup**: Create runs with different statuses
- **Action**: Call `list_runs(status=WorkflowRunStatus.RUNNING)`
- **Expected**: 
  - Returns only RUNNING runs
  - Other statuses excluded

#### 3.5 List Runs Filtered by Workflow
- **Action**: Call `list_runs(workflow_id="wf_123")`
- **Expected**: 
  - Returns only runs for specified workflow
  - Other workflows excluded

### 4. Update Run Status with Database

#### 4.1 Update Run Status Persists
- **Setup**: Create run in database
- **Action**: Call `update_run_status(run_id, status=RUNNING)`
- **Expected**: 
  - Status updated in database
  - Change retrievable via `get_run()`
  - Timestamps updated correctly

#### 4.2 Update Run with Finished Flag
- **Action**: Call `update_run_status(run_id, status=COMPLETED, finished=True)`
- **Expected**: 
  - Status updated to COMPLETED
  - `finished_at` timestamp set
  - Run marked as finished

#### 4.3 Update Run Last Message
- **Action**: Call `update_run_status(run_id, last_message="Processing...")`
- **Expected**: 
  - `last_message` updated in database
  - Message retrievable in run details

#### 4.4 Update Non-Existent Run
- **Action**: Call `update_run_status("nonexistent", ...)`
- **Expected**: 
  - Returns `None` or raises error
  - No database changes

### 5. Node State Operations with Database

#### 5.1 Set Node State Persists
- **Setup**: Create run with workflow graph
- **Action**: Call `set_node_state(run_id, node_id, status=RUNNING, progress=0.5)`
- **Expected**: 
  - Node state saved to database
  - State retrievable via `get_node_state()`
  - Progress stored correctly

#### 5.2 Get Node State from Database
- **Setup**: Create node state in database
- **Action**: Call `get_node_state(run_id, node_id)`
- **Expected**: 
  - Returns state from database
  - All fields populated correctly

#### 5.3 List Node States for Run
- **Setup**: Create run with multiple node states
- **Action**: Call `list_node_states(run_id)`
- **Expected**: 
  - Returns all node states for run
  - States ordered by node_id or execution order
  - All nodes from workflow graph included

#### 5.4 Update Node State Progress
- **Setup**: Create node state with progress 0.3
- **Action**: Call `set_node_state(run_id, node_id, progress=0.7)`
- **Expected**: 
  - Progress updated in database
  - Status may change (e.g., to RUNNING)
  - Change persisted

#### 5.5 Update Node State with Messages
- **Action**: Call `set_node_state(run_id, node_id, messages=["Step 1", "Step 2"])`
- **Expected**: 
  - Messages stored as JSON
  - Messages retrievable correctly
  - JSON deserialization works

#### 5.6 Update Node State with Error
- **Action**: Call `set_node_state(run_id, node_id, error="Error message")`
- **Expected**: 
  - Error stored in database
  - Error retrievable in node state
  - Status may change to FAILED

### 6. Concurrent Operations

#### 6.1 Concurrent Run Creation
- **Setup**: Multiple threads creating runs simultaneously
- **Action**: Create 100 runs concurrently
- **Expected**: 
  - All runs created successfully
  - No ID collisions
  - Database integrity maintained

#### 6.2 Concurrent Node State Updates
- **Setup**: Single run with multiple nodes
- **Action**: Multiple threads updating different nodes
- **Expected**: 
  - All updates succeed
  - No conflicts
  - States remain consistent

#### 6.3 Concurrent Run Status Updates
- **Setup**: Single run
- **Action**: Multiple threads updating status
- **Expected**: 
  - Last write wins (or optimistic locking TBD)
  - No data corruption
  - Status reflects latest change

### 7. Query Performance

#### 7.1 List Runs Performance
- **Setup**: Create 10,000 runs
- **Action**: Measure `list_runs()` execution time
- **Expected**: 
  - Query completes in < 100ms (with indexes)
  - Uses database indexes efficiently
  - Pagination works efficiently

#### 7.2 List Node States Performance
- **Setup**: Run with 100 nodes
- **Action**: Measure `list_node_states(run_id)` execution time
- **Expected**: 
  - Query completes in < 50ms
  - Uses index on run_id
  - Returns all states efficiently

#### 7.3 Filtered Query Performance
- **Setup**: 10,000 runs across 100 projects
- **Action**: Measure `list_runs(project_id="proj_1")` execution time
- **Expected**: 
  - Query uses index on project_id
  - Completes in < 50ms
  - Returns only relevant results

### 8. Data Integrity

#### 8.1 Foreign Key Constraints
- **Setup**: Create run with `workflow_id` referencing non-existent workflow
- **Action**: Attempt to create run
- **Expected**: 
  - Database constraint violation
  - Error thrown
  - Run not created

#### 8.2 Node State Consistency
- **Setup**: Create node state for non-existent run
- **Action**: Attempt to create node state
- **Expected**: 
  - Database constraint violation
  - Error thrown
  - State not created

#### 8.3 Status Enum Validation
- **Action**: Attempt to create run with invalid status
- **Expected**: 
  - Validation error
  - Run not created
  - Error message indicates invalid status

#### 8.4 JSON Structure Validation
- **Action**: Attempt to save invalid JSON in graph_json
- **Expected**: 
  - Validation error
  - Graph not saved
  - Error message indicates invalid JSON

### 9. Workflow Execution Persistence

#### 9.1 Run State Persists Across Restarts
- **Setup**: Create run, update status to RUNNING
- **Action**: Restart service
- **Expected**: 
  - Run state preserved
  - Status remains RUNNING
  - Can continue execution

#### 9.2 Node States Persist Across Restarts
- **Setup**: Create run with node states
- **Action**: Restart service
- **Expected**: 
  - All node states preserved
  - Progress maintained
  - Can resume execution

#### 9.3 Workflow Graph Persists Across Restarts
- **Setup**: Create workflow graph
- **Action**: Restart service
- **Expected**: 
  - Graph preserved
  - Structure intact
  - Available for new runs

## Test Data

### Sample Database Schema
```sql
CREATE TABLE workflow_graphs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    graph_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE workflow_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT,
    output_json TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    last_message TEXT,
    FOREIGN KEY(project_id) REFERENCES projects(id),
    FOREIGN KEY(workflow_id) REFERENCES workflow_graphs(id)
);

CREATE TABLE workflow_node_states (
    run_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    messages_json TEXT,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    PRIMARY KEY (run_id, node_id),
    FOREIGN KEY(run_id) REFERENCES workflow_runs(id)
);
```

## Edge Cases

1. **Very Large Graphs**: Graphs with 100+ nodes
2. **Very Long Runs**: Runs taking hours/days
3. **Many Node States**: Runs with 1000+ node state updates
4. **Concurrent Executions**: Multiple runs of same workflow
5. **Graph Updates During Execution**: Updating graph while runs active
6. **Database Connection Failures**: Handling connection errors
7. **JSON Size Limits**: Very large JSON structures

## Dependencies

- Database (SQLite for tests, PostgreSQL for production)
- Database migration framework
- ORM or raw SQL
- JSON handling library
- Connection pooling
- Transaction management

## Test Implementation Notes

- Use in-memory SQLite for fast unit tests
- Use PostgreSQL for integration tests
- Test JSON serialization/deserialization
- Use database transactions that rollback after tests
- Test concurrent operations for race conditions
- Verify indexes are used
- Test with realistic data volumes
- Mock database failures for error handling tests
- Test workflow execution persistence


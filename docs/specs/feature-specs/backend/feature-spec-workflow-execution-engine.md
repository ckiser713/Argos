# Feature Specification: Workflow Execution Engine

## Overview

Implementation specification for the core workflow execution engine using LangGraph, including graph compilation, state management, node execution tracking, and event handling.

## Current State

- `WorkflowService.create_run()` creates run records but doesn't execute them
- Workflow runs are created with status PENDING but never transition to RUNNING
- No actual LangGraph execution for workflow runs
- Agent runs have LangGraph execution, but workflow runs don't
- Workflow node states can be set manually but aren't updated during execution

## Target State

- Workflow runs execute when explicitly triggered by the execute endpoint
- LangGraph graphs are compiled from workflow graph definitions
- Node states update in real-time during execution
- Execution errors are handled gracefully
- Workflow runs can be cancelled mid-execution
- Execution progress is tracked and streamed

## Requirements

### Functional Requirements

1. Execute workflow runs using LangGraph
2. Compile workflow graphs to LangGraph StateGraph
3. Track node execution state in real-time
4. Handle execution errors and failures
5. Support workflow cancellation
6. Stream execution events via WebSocket/SSE
7. Persist execution state to database
8. Support conditional edges and branching
9. Handle long-running workflows
10. Support workflow retries

### Non-Functional Requirements

1. Fast workflow compilation (< 500ms)
2. Efficient state management
3. Scalable execution (background tasks)
4. Error recovery mechanisms
5. Observability (logging, metrics)

## Technical Design

### Workflow Execution Flow

```
1. Create workflow run (PENDING)
2. Background task picks up run
3. Load workflow graph from DB
4. Compile graph to LangGraph StateGraph
5. Update run status to RUNNING
6. Execute graph with input data
7. Stream events and update node states
8. On completion: Update run status to COMPLETED/FAILED
9. Persist final output
```

### LangGraph Compilation

#### Graph Compilation Service

```python
class WorkflowGraphCompiler:
    def compile(self, workflow_graph: WorkflowGraph) -> StateGraph:
        """Compile workflow graph to LangGraph StateGraph."""
        graph = StateGraph(WorkflowState)
        
        # Add nodes
        for node in workflow_graph.nodes:
            graph.add_node(node.id, self._create_node_function(node))
        
        # Add edges
        for edge in workflow_graph.edges:
            if edge.condition:
                graph.add_conditional_edges(
                    edge.from_node_id,
                    self._create_condition_function(edge),
                    {edge.condition: edge.to_node_id}
                )
            else:
                graph.add_edge(edge.from_node_id, edge.to_node_id)
        
        # Set entry point
        entry_node = self._find_entry_node(workflow_graph)
        graph.set_entry_point(entry_node.id)
        
        return graph.compile()
```

#### Node Function Creation

```python
def _create_node_function(self, node: WorkflowNode):
    """Create executable function for workflow node."""
    async def node_function(state: WorkflowState):
        # Update node state to RUNNING
        workflow_service.set_node_state(
            run_id=state.run_id,
            node_id=node.id,
            status=WorkflowNodeStatus.RUNNING,
            started=True,
            progress=0.0,
        )
        
        try:
            # Execute node logic based on node type
            if node.type == "llm":
                result = await self._execute_llm_node(node, state)
            elif node.type == "tool":
                result = await self._execute_tool_node(node, state)
            elif node.type == "condition":
                result = await self._evaluate_condition(node, state)
            else:
                result = await self._execute_custom_node(node, state)
            
            # Update node state to COMPLETED
            workflow_service.set_node_state(
                run_id=state.run_id,
                node_id=node.id,
                status=WorkflowNodeStatus.COMPLETED,
                completed=True,
                progress=1.0,
            )
            
            return {"output": result}
        except Exception as e:
            # Update node state to FAILED
            workflow_service.set_node_state(
                run_id=state.run_id,
                node_id=node.id,
                status=WorkflowNodeStatus.FAILED,
                completed=True,
                error=str(e),
            )
            raise
    
    return node_function
```

### Workflow Execution Service

#### Execution Method

```python
async def execute_workflow_run(self, run_id: str):
    """Execute a workflow run using LangGraph."""
    run = self.get_run(run_id)
    if not run:
        return
    
    workflow_graph = self.get_graph(run.workflow_id)
    if not workflow_graph:
        self.update_run_status(run_id, WorkflowRunStatus.FAILED, 
                              last_message="Workflow graph not found")
        return
    
    # Update run status
    self.update_run_status(run_id, WorkflowRunStatus.RUNNING,
                          last_message="Starting workflow execution")
    
    try:
        # Compile graph
        compiler = WorkflowGraphCompiler()
        compiled_graph = compiler.compile(workflow_graph)
        
        # Prepare initial state
        initial_state = {
            "run_id": run_id,
            "project_id": run.project_id,
            "input": run.input_json or {},
            "output": {},
            "messages": [],
        }
        
        # Execute graph
        async for event in compiled_graph.astream_events(
            initial_state,
            version="v1"
        ):
            # Handle events
            await self._handle_execution_event(run_id, event)
        
        # Update run status to completed
        final_state = await compiled_graph.ainvoke(initial_state)
        self.update_run_status(
            run_id,
            WorkflowRunStatus.COMPLETED,
            last_message="Workflow execution completed",
            finished=True,
            output_data=final_state.get("output", {})
        )
        
    except Exception as e:
        logger.exception(f"Workflow execution failed: {e}")
        self.update_run_status(
            run_id,
            WorkflowRunStatus.FAILED,
            last_message=f"Workflow execution failed: {str(e)}",
            finished=True
        )
```

#### Event Handling

```python
async def _handle_execution_event(self, run_id: str, event: dict):
    """Handle LangGraph execution events."""
    event_type = event.get("event")
    name = event.get("name", "")
    
    if event_type == "on_chain_start":
        # Node started
        self.set_node_state(
            run_id,
            name,
            status=WorkflowNodeStatus.RUNNING,
            started=True,
            progress=0.0
        )
        # Emit WebSocket event
        emit_workflow_event(
            project_id=run.project_id,
            event_type="workflow.node.started",
            node_state_data={"node_id": name, "run_id": run_id}
        )
    
    elif event_type == "on_chain_end":
        # Node completed
        self.set_node_state(
            run_id,
            name,
            status=WorkflowNodeStatus.COMPLETED,
            completed=True,
            progress=1.0
        )
        emit_workflow_event(
            project_id=run.project_id,
            event_type="workflow.node.completed",
            node_state_data={"node_id": name, "run_id": run_id}
        )
    
    elif event_type == "on_chain_error":
        # Node failed
        error = event.get("error", "Unknown error")
        self.set_node_state(
            run_id,
            name,
            status=WorkflowNodeStatus.FAILED,
            completed=True,
            error=str(error)
        )
        emit_workflow_event(
            project_id=run.project_id,
            event_type="workflow.node.failed",
            node_state_data={"node_id": name, "run_id": run_id, "error": str(error)}
        )
```

### Cancellation Support

#### Cancel Method

```python
async def cancel_workflow_run(self, run_id: str) -> WorkflowRun:
    """Cancel a running workflow."""
    run = self.get_run(run_id)
    if not run:
        raise ValueError("Workflow run not found")
    
    if run.status not in [WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING]:
        raise ValueError(f"Cannot cancel run with status: {run.status}")
    
    # Update status
    self.update_run_status(
        run_id,
        WorkflowRunStatus.CANCELLED,
        last_message="Workflow execution cancelled",
        finished=True
    )
    
    # Cancel all running nodes
    node_states = self.list_node_states(run_id)
    for node_state in node_states:
        if node_state.status == WorkflowNodeStatus.RUNNING:
            self.set_node_state(
                run_id,
                node_state.node_id,
                status=WorkflowNodeStatus.CANCELLED,
                completed=True
            )
    
    return self.get_run(run_id)
```

### Background Task Integration

#### Route Handler Update

```python
@router.post("/projects/{project_id}/workflows/runs")
async def create_workflow_run(
    project_id: str,
    body: CreateWorkflowRunRequest,
    background_tasks: BackgroundTasks
) -> WorkflowRun:
    graph = workflow_service.get_graph(body.workflow_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    run = workflow_service.create_run(
        project_id=project_id,
        workflow_id=body.workflow_id,
        input_data=body.input_data,
    )
    
    # Do not automatically schedule execution; it will be triggered via the execute endpoint
    
    return run
```

## Database Schema

### Existing Tables

- `workflow_graphs` - Graph definitions
- `workflow_runs` - Run records
- `workflow_node_states` - Node execution states

### No Schema Changes Required

- Existing schema supports execution tracking

## Implementation Steps

1. **Create WorkflowGraphCompiler class**
   - Compile workflow graphs to LangGraph
   - Handle node types and edge conditions
   - Support custom node functions

2. **Implement execute_workflow_run method**
   - Load workflow graph
   - Compile to LangGraph
   - Execute with event streaming
   - Handle errors

3. **Add event handling**
   - Process LangGraph events
   - Update node states
   - Emit WebSocket events

4. **Add cancellation support**
   - Cancel running workflows
   - Update node states
   - Handle cleanup

5. **Add tests**
   - Test graph compilation
   - Test execution flow
   - Test error handling
   - Test cancellation

## Testing Strategy

### Unit Tests

- Test graph compilation
- Test node function creation
- Test event handling
- Test cancellation logic

### Integration Tests

- Test full workflow execution
- Test with real LangGraph
- Test error scenarios
- Test cancellation

### Performance Tests

- Test long-running workflows
- Test concurrent executions
- Test memory usage

## Success Criteria

1. Workflow runs execute automatically when created
2. Node states update in real-time
3. Execution errors are handled gracefully
4. Workflows can be cancelled
5. Events stream via WebSocket
6. Tests pass
7. Performance is acceptable

## Notes

- Consider workflow versioning for backward compatibility
- Optimize graph compilation (cache compiled graphs)
- Handle very long-running workflows (checkpointing)
- Consider workflow templates/predefined graphs
- Support workflow debugging mode (step-by-step execution)
- Add workflow execution metrics and monitoring


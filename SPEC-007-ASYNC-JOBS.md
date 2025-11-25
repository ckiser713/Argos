Goal: Ensure the UI never freezes while the backend crunches numbers.

Markdown

# SPEC-007: Async Worker & Job Queue

## Context
Ingesting a 100MB PDF or generating a roadmap takes time (10s - 2min). This cannot happen in the request/response cycle of FastAPI.

## Tech Stack
- **FastAPI BackgroundTasks:** For simple V1 implementation (no Redis required yet).
- **Streaming:** The worker updates the `AgentRun` status in the DB, and the WebSocket endpoint polls/watches this status.

## Implementation Guide

### 1. Refactor Routes (`app/api/routes/agents.py`)
```python
from fastapi import BackgroundTasks

@router.post("/runs")
async def create_run(
    request: AgentRunRequest, 
    background_tasks: BackgroundTasks
):
    # 1. Create DB Record
    run = agent_service.create_run_record(request)
    
    # 2. Offload Execution
    background_tasks.add_task(agent_service.execute_run, run.id)
    
    return run
2. The Worker Logic (app/services/agent_service.py)
Python

async def execute_run(run_id: str):
    run = get_run(run_id)
    update_status(run_id, "RUNNING")
    
    try:
        # Invoke LangGraph (SPEC-005)
        final_state = project_manager_graph.invoke(
            {"messages": [HumanMessage(content=run.input_prompt)]}
        )
        save_result(run_id, final_state['messages'][-1].content)
        update_status(run_id, "COMPLETED")
    except Exception as e:
        update_status(run_id, "FAILED", error=str(e))
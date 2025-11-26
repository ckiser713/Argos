from __future__ import annotations

import json
from typing import List, Optional

from app.domain.common import PaginatedResponse
from app.domain.models import (
    AgentMessage,
    AgentNodeState,
    AgentProfile,
    AgentRun,
    AgentRunRequest,
    AgentRunStatus,
    AppendMessageRequest,
)
from app.graphs.project_manager_graph import app as project_manager_graph
from app.services.agent_service import agent_service
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

router = APIRouter()


@router.get("/profiles", response_model=List[AgentProfile], summary="List available agents")
def list_agent_profiles() -> List[AgentProfile]:
    return agent_service.list_agents()


@router.get("/profiles/{agent_id}", response_model=AgentProfile, summary="Get a single agent profile")
def get_agent_profile(agent_id: str) -> AgentProfile:
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/projects/{project_id}/agent-runs", response_model=List[AgentRun], summary="List agent runs")
def list_agent_runs(project_id: str) -> List[AgentRun]:
    runs = agent_service.list_runs(project_id=project_id)
    return runs if isinstance(runs, list) else runs.items if hasattr(runs, 'items') else []


@router.get("/projects/{project_id}/agent-runs/{run_id}", response_model=AgentRun, summary="Get a single agent run")
def get_agent_run(project_id: str, run_id: str) -> AgentRun:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.post("/projects/{project_id}/agent-runs", response_model=AgentRun, summary="Start an agent run")
async def create_agent_run(project_id: str, request: AgentRunRequest, background_tasks: BackgroundTasks):
    request_project_id = request.project_id or project_id
    if request.project_id and request.project_id != project_id:
        raise HTTPException(status_code=400, detail="Project ID mismatch")

    agent = agent_service.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create DB Record
    run = agent_service.create_run_record(request.model_copy(update={"project_id": request_project_id}))

    # Offload Execution
    background_tasks.add_task(agent_service.execute_run, run.id)

    return run


@router.get(
    "/projects/{project_id}/agent-runs/{run_id}/steps",
    response_model=PaginatedResponse,
    summary="List steps for agent run",
)
def list_agent_run_steps(
    project_id: str,
    run_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return agent_service.list_steps(run_id, cursor=cursor, limit=limit)


@router.get(
    "/projects/{project_id}/agent-runs/{run_id}/messages",
    response_model=PaginatedResponse,
    summary="List messages for agent run",
)
def list_agent_run_messages(
    project_id: str,
    run_id: str,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return agent_service.list_messages(run_id, cursor=cursor, limit=limit)


@router.post(
    "/projects/{project_id}/agent-runs/{run_id}/messages",
    response_model=AgentMessage,
    status_code=201,
    summary="Append user message to agent run",
)
def append_agent_run_message(
    project_id: str,
    run_id: str,
    request: AppendMessageRequest,
) -> AgentMessage:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]:
        # May restart run if completed
        if run.status == AgentRunStatus.COMPLETED:
            agent_service.update_run(run_id, status=AgentRunStatus.PENDING)

    return agent_service.append_message(run_id, request)


@router.get(
    "/projects/{project_id}/agent-runs/{run_id}/node-states",
    response_model=List[AgentNodeState],
    summary="List node states for agent run",
)
def list_agent_run_node_states(
    project_id: str,
    run_id: str,
) -> List[AgentNodeState]:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    return agent_service.list_node_states(run_id)


@router.post("/projects/{project_id}/agent-runs/{run_id}/cancel", response_model=AgentRun, summary="Cancel agent run")
def cancel_agent_run(
    project_id: str,
    run_id: str,
) -> AgentRun:
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    if run.status in [AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Run cannot be cancelled. Current status: {run.status.value}")

    return agent_service.cancel_run(run_id)


@router.get("/projects/{project_id}/agent-runs/{run_id}/stream")
async def stream_agent_run(project_id: str, run_id: str):
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Agent run not found")

    async def event_generator():
        async for event in project_manager_graph.astream_events(
            {"messages": [HumanMessage(content=run.input_prompt or "")], "project_id": run.project_id}, version="v1"
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

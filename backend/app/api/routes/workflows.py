import asyncio
from typing import List, Optional

from app.domain.models import WorkflowGraph, WorkflowRun, WorkflowRunStatus
from app.services.workflow_service import workflow_service
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CreateWorkflowRunRequest(BaseModel):
    workflow_id: str
    input_data: Optional[dict] = None


class ExecuteWorkflowRunRequest(BaseModel):
    input_data: Optional[dict] = None


class ResumeWorkflowRunRequest(BaseModel):
    checkpoint_id: Optional[str] = None


@router.get(
    "/projects/{project_id}/workflows/graphs",
    response_model=List[WorkflowGraph],
    summary="List available workflow graphs for a project",
)
def list_workflow_graphs(project_id: str) -> List[WorkflowGraph]:
    return workflow_service.list_graphs(project_id=project_id)


@router.get(
    "/projects/{project_id}/workflows/graphs/{workflow_id}",
    response_model=WorkflowGraph,
    summary="Get a workflow graph by ID",
)
def get_workflow_graph(project_id: str, workflow_id: str) -> WorkflowGraph:
    graph = workflow_service.get_graph(workflow_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return graph


@router.post(
    "/projects/{project_id}/workflows/runs", response_model=WorkflowRun, status_code=201, summary="Start a workflow run"
)
def create_workflow_run(
    project_id: str, body: CreateWorkflowRunRequest, background_tasks: BackgroundTasks
) -> WorkflowRun:
    graph = workflow_service.get_graph(body.workflow_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = workflow_service.create_run(
        project_id=project_id,
        workflow_id=body.workflow_id,
        input_data=body.input_data,
    )

    # Schedule execution in background
    background_tasks.add_task(workflow_service.execute_workflow_run, run.id)

    return run


@router.get(
    "/projects/{project_id}/workflows/runs",
    response_model=List[WorkflowRun],
    summary="List workflow runs for a project",
)
def list_workflow_runs(project_id: str, workflow_id: Optional[str] = None) -> List[WorkflowRun]:
    return workflow_service.list_runs(project_id=project_id, workflow_id=workflow_id)


@router.get(
    "/projects/{project_id}/workflows/runs/{run_id}", response_model=WorkflowRun, summary="Get a workflow run by ID"
)
def get_workflow_run(project_id: str, run_id: str) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run


@router.post(
    "/projects/{project_id}/workflows/runs/{run_id}/execute",
    response_model=WorkflowRun,
    status_code=202,
    summary="Execute a workflow run",
)
async def execute_workflow_run(
    project_id: str,
    run_id: str,
    body: Optional[ExecuteWorkflowRunRequest] = None,
    background_tasks: BackgroundTasks = None,
) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if run.status == WorkflowRunStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Workflow run is already executing")

    if run.status == WorkflowRunStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Workflow run already completed")

    # Update input data if provided
    if body and body.input_data:
        import json

        from app.db import db_session

        with db_session() as conn:
            conn.execute("UPDATE workflow_runs SET input_json = ? WHERE id = ?", (json.dumps(body.input_data), run_id))
            conn.commit()

    # Schedule execution
    if background_tasks:
        background_tasks.add_task(workflow_service.execute_workflow_run, run_id)
    else:
        asyncio.create_task(workflow_service.execute_workflow_run(run_id))

    return workflow_service.get_run(run_id)


@router.post(
    "/projects/{project_id}/workflows/runs/{run_id}/cancel", response_model=WorkflowRun, summary="Cancel a workflow run"
)
async def cancel_workflow_run(project_id: str, run_id: str) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    try:
        return await workflow_service.cancel_workflow_run(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/projects/{project_id}/workflows/runs/{run_id}/pause", response_model=WorkflowRun, summary="Pause a workflow run"
)
async def pause_workflow_run(project_id: str, run_id: str) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    try:
        return await workflow_service.pause_workflow_run(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/projects/{project_id}/workflows/runs/{run_id}/resume",
    response_model=WorkflowRun,
    status_code=202,
    summary="Resume a paused workflow run",
)
async def resume_workflow_run(
    project_id: str, run_id: str, body: Optional[ResumeWorkflowRunRequest] = None
) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    try:
        return await workflow_service.resume_workflow_run(run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/workflows/runs/{run_id}/status", summary="Get workflow run execution status")
def get_workflow_run_status(project_id: str, run_id: str) -> dict:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    try:
        return workflow_service.get_execution_status(run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

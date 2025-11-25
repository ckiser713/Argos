from typing import List

from fastapi import APIRouter, HTTPException

from app.domain.models import WorkflowGraph, WorkflowRun
from app.services.workflow_service import workflow_service

router = APIRouter()


@router.get("/graphs", response_model=List[WorkflowGraph], summary="List available workflow graphs")
def list_workflow_graphs() -> List[WorkflowGraph]:
    return workflow_service.list_graphs()


@router.get("/graphs/{workflow_id}", response_model=WorkflowGraph, summary="Get a workflow graph by ID")
def get_workflow_graph(workflow_id: str) -> WorkflowGraph:
    graph = workflow_service.get_graph(workflow_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return graph


@router.post("/runs", response_model=WorkflowRun, summary="Start a workflow run (stubbed)")
def create_workflow_run(workflow_id: str) -> WorkflowRun:
    graph = workflow_service.get_graph(workflow_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow_service.create_run(workflow_id)


@router.get("/runs", response_model=List[WorkflowRun], summary="List workflow runs")
def list_workflow_runs() -> List[WorkflowRun]:
    return workflow_service.list_runs()


@router.get("/runs/{run_id}", response_model=WorkflowRun, summary="Get a workflow run by ID")
def get_workflow_run(run_id: str) -> WorkflowRun:
    run = workflow_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run

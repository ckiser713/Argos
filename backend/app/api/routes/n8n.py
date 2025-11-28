"""
API routes for n8n workflow management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.n8n_service import n8n_service

router = APIRouter()


@router.get("/n8n/workflows", summary="List available n8n workflows")
async def list_workflows() -> List[dict]:
    """
    List all available n8n workflows.
    """
    workflows = await n8n_service.list_workflows()
    return workflows


@router.get("/n8n/workflows/{workflow_id}", summary="Get workflow details")
async def get_workflow(workflow_id: str) -> dict:
    """
    Get details for a specific workflow.
    """
    workflow = await n8n_service.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/n8n/workflows/{workflow_id}/executions", summary="Get workflow executions")
async def get_workflow_executions(
    workflow_id: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> List[dict]:
    """
    Get recent executions for a workflow.
    """
    executions = await n8n_service.get_workflow_executions(workflow_id=workflow_id, limit=limit)
    return executions


@router.get("/n8n/templates", summary="Get workflow templates")
def get_workflow_templates() -> List[dict]:
    """
    Get predefined workflow templates for common automation tasks.
    
    These templates can be used as starting points for creating n8n workflows.
    """
    templates = n8n_service.get_workflow_templates()
    return templates


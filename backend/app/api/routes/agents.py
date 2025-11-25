from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.domain.models import (
    AgentProfile,
    AgentRun,
    AgentRunRequest,
)
from app.services.agent_service import agent_service

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


@router.get("/runs", response_model=List[AgentRun], summary="List agent runs")
def list_agent_runs() -> List[AgentRun]:
    return agent_service.list_runs()


@router.post("/runs", response_model=AgentRun, summary="Start an agent run")
async def create_agent_run(
    request: AgentRunRequest, 
    background_tasks: BackgroundTasks
):
    agent = agent_service.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    # 1. Create DB Record
    run = agent_service.create_run_record(request)
    
    # 2. Offload Execution
    background_tasks.add_task(agent_service.execute_run, run.id)
    
    return run


@router.get("/runs/{run_id}", response_model=AgentRun, summary="Get agent run by ID")
def get_agent_run(run_id: str) -> AgentRun:
    run = agent_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run

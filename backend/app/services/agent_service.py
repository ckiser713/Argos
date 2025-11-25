from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.domain.models import (
    AgentProfile,
    AgentRun,
    AgentRunRequest,
    AgentRunStatus,
)


class AgentService:
    """
    In-memory agent registry and runs.

    Runs are created as PENDING; streaming endpoints advance them deterministically.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentProfile] = {
            "researcher": AgentProfile(
                id="researcher",
                name="Deep Researcher",
                description="Performs exhaustive research over ingested artifacts.",
                capabilities=["deep_research", "citation", "summarization"],
            ),
            "planner": AgentProfile(
                id="planner",
                name="Strategy Planner",
                description="Turns ideas and research into roadmaps.",
                capabilities=["planning", "decomposition", "timeline_synthesis"],
            ),
        }
        self._runs: Dict[str, AgentRun] = {}

    def list_agents(self) -> List[AgentProfile]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        return self._agents.get(agent_id)

    def list_runs(self) -> List[AgentRun]:
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[AgentRun]:
        return self._runs.get(run_id)

    def create_run(self, request: AgentRunRequest) -> AgentRun:
        run_id = f"agent_run_{len(self._runs) + 1}"
        now = datetime.utcnow()
        run = AgentRun(
            id=run_id,
            agent_id=request.agent_id,
            status=AgentRunStatus.PENDING,
            started_at=now,
            finished_at=None,
            input_prompt=request.input_prompt,
            output_summary=None,
        )
        self._runs[run_id] = run
        return run

    def update_run(
        self,
        run_id: str,
        *,
        status: Optional[AgentRunStatus] = None,
        output_summary: Optional[str] = None,
        finished: bool | None = None,
    ) -> Optional[AgentRun]:
        run = self._runs.get(run_id)
        if not run:
            return None

        data = run.model_dump()
        if status is not None:
            data["status"] = status
        if output_summary is not None:
            data["output_summary"] = output_summary
        if finished:
            data["finished_at"] = datetime.utcnow()

        updated = AgentRun(**data)
        self._runs[run_id] = updated
        return updated


agent_service = AgentService()

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.db import db_session
from app.domain.models import (
    AgentProfile,
    AgentRun,
    AgentRunRequest,
    AgentRunStatus,
)
from app.graphs.project_manager_graph import app as project_manager_graph


class AgentService:
    """
    Agent registry and runs using DB.

    Runs are created as PENDING; background tasks advance them.
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

    def list_agents(self) -> List[AgentProfile]:
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        return self._agents.get(agent_id)

    def list_runs(self) -> List[AgentRun]:
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM agent_runs").fetchall()
            return [AgentRun(**dict(row)) for row in rows]

    def get_run(self, run_id: str) -> Optional[AgentRun]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
            if row:
                return AgentRun(**dict(row))
        return None

    def create_run_record(self, request: AgentRunRequest) -> AgentRun:
        run_id = f"agent_run_{datetime.now(timezone.utc).timestamp()}"
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=run_id,
            project_id=request.project_id,
            status=AgentRunStatus.PENDING,
            started_at=now,
            finished_at=None,
            input_prompt=request.input_prompt,
            output_summary=None,
        )
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs (id, project_id, status, input_prompt, output_summary, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run.id, run.project_id, run.status, run.input_prompt, run.output_summary, run.started_at.isoformat(), run.finished_at.isoformat() if run.finished_at else None)
            )
            conn.commit()
        return run

    def update_run(
        self,
        run_id: str,
        *,
        status: Optional[AgentRunStatus] = None,
        output_summary: Optional[str] = None,
        finished: bool | None = None,
    ) -> Optional[AgentRun]:
        run = self.get_run(run_id)
        if not run:
            return None

        if status is not None:
            run.status = status
        if output_summary is not None:
            run.output_summary = output_summary
        if finished:
            run.finished_at = datetime.now(timezone.utc)

        with db_session() as conn:
            conn.execute(
                """
                UPDATE agent_runs SET status = ?, output_summary = ?, finished_at = ? WHERE id = ?
                """,
                (run.status, run.output_summary, run.finished_at.isoformat() if run.finished_at else None, run_id)
            )
            conn.commit()
        return run

    async def execute_run(self, run_id: str):
        run = self.get_run(run_id)
        if not run:
            return
        self.update_run(run_id, status=AgentRunStatus.RUNNING)
        
        try:
            # Invoke LangGraph (SPEC-005)
            final_state = project_manager_graph.invoke(
                {"messages": [HumanMessage(content=run.input_prompt)], "project_id": run.project_id}
            )
            self.update_run(run_id, output_summary=final_state['messages'][-1].content, status=AgentRunStatus.COMPLETED, finished=True)
        except Exception as e:
            self.update_run(run_id, status=AgentRunStatus.FAILED, finished=True)


agent_service = AgentService()

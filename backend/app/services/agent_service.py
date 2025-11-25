from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage

from app.db import db_session
from app.domain.common import PaginatedResponse
from app.domain.models import (
    AgentMessage,
    AgentMessageRole,
    AgentNodeState,
    AgentProfile,
    AgentRun,
    AgentRunRequest,
    AgentRunStatus,
    AgentStep,
    AgentStepStatus,
    AppendMessageRequest,
)
from app.services.streaming_service import emit_agent_event


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

    def list_runs(self, project_id: Optional[str] = None) -> List[AgentRun]:
        with db_session() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM agent_runs WHERE project_id = ? ORDER BY started_at DESC", (project_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM agent_runs ORDER BY started_at DESC").fetchall()
            return [self._row_to_run(row) for row in rows]

    def get_run(self, run_id: str) -> Optional[AgentRun]:
        with db_session() as conn:
            row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
            if row:
                return self._row_to_run(row)
        return None

    def create_run_record(self, request: AgentRunRequest) -> AgentRun:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        run = AgentRun(
            id=run_id,
            project_id=request.project_id,
            agent_id=request.agent_id,
            status=AgentRunStatus.PENDING,
            started_at=now,
            finished_at=None,
            input_prompt=request.input_prompt,
            input_query=request.input_prompt,
            output_summary=None,
            context_item_ids=request.context_item_ids if hasattr(request, "context_item_ids") else [],
        )
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO agent_runs
                (id, project_id, agent_id, status, input_prompt, output_summary, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.project_id,
                    run.agent_id,
                    run.status.value,
                    run.input_prompt,
                    run.output_summary,
                    run.started_at.isoformat(),
                    run.finished_at.isoformat() if run.finished_at else None,
                ),
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
                (
                    run.status.value,
                    run.output_summary,
                    run.finished_at.isoformat() if run.finished_at else None,
                    run_id,
                ),
            )
            conn.commit()
        
        # Emit run updated event if status changed
        if status:
            event_type_map = {
                AgentRunStatus.RUNNING: "agent.run.started",
                AgentRunStatus.COMPLETED: "agent.run.completed",
                AgentRunStatus.FAILED: "agent.run.failed",
                AgentRunStatus.CANCELLED: "agent.run.cancelled",
            }
            event_type = event_type_map.get(status, "agent.run.updated")
            asyncio.create_task(
                emit_agent_event(run.project_id, event_type, run_data=run.model_dump())
            )
        
        return run

    def cancel_run(self, run_id: str) -> AgentRun:
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            conn.execute(
                """
                UPDATE agent_runs
                SET status = ?, finished_at = ?
                WHERE id = ?
                """,
                (AgentRunStatus.CANCELLED.value, now.isoformat(), run_id),
            )
            conn.commit()
        
        updated_run = self.get_run(run_id)
        
        # Emit run cancelled event
        if updated_run:
            asyncio.create_task(
                emit_agent_event(updated_run.project_id, "agent.run.cancelled", run_data=updated_run.model_dump())
            )
        
        return updated_run

    def list_steps(
        self,
        run_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM agent_steps WHERE run_id = ? ORDER BY step_number ASC LIMIT ?"
            params = [run_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_step(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute("SELECT COUNT(*) as total FROM agent_steps WHERE run_id = ?", (run_id,)).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def create_step(
        self,
        run_id: str,
        step_number: int,
        node_id: Optional[str] = None,
        status: AgentStepStatus = AgentStepStatus.PENDING,
    ) -> AgentStep:
        step_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        step = AgentStep(
            id=step_id,
            run_id=run_id,
            step_number=step_number,
            node_id=node_id,
            status=status,
            started_at=now,
        )
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO agent_steps
                (id, run_id, step_number, node_id, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    step.id,
                    step.run_id,
                    step.step_number,
                    step.node_id,
                    step.status.value,
                    step.started_at.isoformat(),
                ),
            )
            conn.commit()
        return step

    def update_step(
        self,
        step_id: str,
        *,
        status: Optional[AgentStepStatus] = None,
        input: Optional[str] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
        completed: bool = False,
    ) -> Optional[AgentStep]:
        with db_session() as conn:
            updates = []
            params = []

            if status:
                updates.append("status = ?")
                params.append(status.value)
            if input:
                updates.append("input_json = ?")
                params.append(json.dumps(input))
            if output:
                updates.append("output_json = ?")
                params.append(json.dumps(output))
            if error:
                updates.append("error = ?")
                params.append(error)
            if duration_ms is not None:
                updates.append("duration_ms = ?")
                params.append(duration_ms)
            if completed:
                updates.append("completed_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())

            if updates:
                params.append(step_id)
                query = f"UPDATE agent_steps SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute("SELECT * FROM agent_steps WHERE id = ?", (step_id,)).fetchone()
            if row:
                return self._row_to_step(row)
        return None

    def list_messages(
        self,
        run_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> PaginatedResponse:
        with db_session() as conn:
            query = "SELECT * FROM agent_messages WHERE run_id = ? ORDER BY created_at ASC LIMIT ?"
            params = [run_id, limit + 1]

            rows = conn.execute(query, params).fetchall()

            items = [self._row_to_message(row) for row in rows[:limit]]

            next_cursor = None
            if len(rows) > limit:
                next_cursor = rows[limit]["id"]

            total_row = conn.execute(
                "SELECT COUNT(*) as total FROM agent_messages WHERE run_id = ?", (run_id,)
            ).fetchone()
            total = total_row["total"] if total_row else len(items)

            return PaginatedResponse(items=items, next_cursor=next_cursor, total=total)

    def append_message(self, run_id: str, request: AppendMessageRequest) -> AgentMessage:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        message = AgentMessage(
            id=message_id,
            run_id=run_id,
            role=AgentMessageRole.USER,
            content=request.content,
            context_item_ids=request.context_item_ids,
            created_at=now,
        )
        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO agent_messages
                (id, run_id, role, content, context_item_ids_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.run_id,
                    message.role.value,
                    message.content,
                    json.dumps(message.context_item_ids),
                    message.created_at.isoformat(),
                ),
            )
            conn.commit()
        
        # Emit message appended event
        run = self.get_run(run_id)
        if run:
            asyncio.create_task(
                emit_agent_event(run.project_id, "agent.message.appended", message_data=message.model_dump())
            )
        
        return message

    def list_node_states(self, run_id: str) -> List[AgentNodeState]:
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM agent_node_states WHERE run_id = ?", (run_id,)).fetchall()
            return [self._row_to_node_state(row) for row in rows]

    def update_node_state(
        self,
        run_id: str,
        node_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        messages: Optional[List[str]] = None,
        error: Optional[str] = None,
        started: bool = False,
        completed: bool = False,
    ) -> AgentNodeState:
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT * FROM agent_node_states WHERE run_id = ? AND node_id = ?", (run_id, node_id)
            ).fetchone()

            if existing:
                updates = []
                params = []

                if status:
                    updates.append("status = ?")
                    params.append(status)
                if progress is not None:
                    updates.append("progress = ?")
                    params.append(progress)
                if messages is not None:
                    updates.append("messages_json = ?")
                    params.append(json.dumps(messages))
                if error:
                    updates.append("error = ?")
                    params.append(error)
                if started:
                    updates.append("started_at = ?")
                    params.append(now.isoformat())
                if completed:
                    updates.append("completed_at = ?")
                    params.append(now.isoformat())

                if updates:
                    params.extend([run_id, node_id])
                    query = f"UPDATE agent_node_states SET {', '.join(updates)} WHERE run_id = ? AND node_id = ?"
                    conn.execute(query, params)
            else:
                conn.execute(
                    """
                    INSERT INTO agent_node_states
                    (run_id, node_id, status, progress, messages_json, started_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        node_id,
                        status or "pending",
                        progress or 0.0,
                        json.dumps(messages or []),
                        now.isoformat() if started else None,
                    ),
                )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM agent_node_states WHERE run_id = ? AND node_id = ?", (run_id, node_id)
            ).fetchone()
            return self._row_to_node_state(row)

    async def execute_run(self, run_id: str):
        run = self.get_run(run_id)
        if not run:
            return
        self.update_run(run_id, status=AgentRunStatus.RUNNING)

        try:
            # Track node states during LangGraph execution
            from app.graphs.project_manager_graph import app as langgraph_app

            # Initialize node states
            self.update_node_state(run_id, "agent", status="running", started=True)

            # Stream events from LangGraph
            async for event in langgraph_app.astream_events(
                {"messages": [HumanMessage(content=run.input_prompt or "")], "project_id": run.project_id},
                version="v1",
            ):
                # Track node execution
                if event.get("event") == "on_chain_start":
                    node_name = event.get("name", "")
                    if node_name in ["agent", "tools"]:
                        node_state = self.update_node_state(
                            run_id,
                            node_name,
                            status="running",
                            started=True,
                            progress=0.0,
                        )
                        # Emit node started event
                        if node_state:
                            asyncio.create_task(
                                emit_agent_event(
                                    run.project_id,
                                    "agent.step.started",
                                    node_state_data=node_state.model_dump(),
                                )
                            )

                elif event.get("event") == "on_chain_end":
                    node_name = event.get("name", "")
                    if node_name in ["agent", "tools"]:
                        node_state = self.update_node_state(
                            run_id,
                            node_name,
                            status="completed",
                            completed=True,
                            progress=1.0,
                        )
                        # Emit node completed event
                        if node_state:
                            asyncio.create_task(
                                emit_agent_event(
                                    run.project_id,
                                    "agent.step.completed",
                                    node_state_data=node_state.model_dump(),
                                )
                            )

                elif event.get("event") == "on_chain_error":
                    node_name = event.get("name", "")
                    error_msg = str(event.get("error", "Unknown error"))
                    if node_name in ["agent", "tools"]:
                        node_state = self.update_node_state(
                            run_id,
                            node_name,
                            status="failed",
                            error=error_msg,
                            completed=True,
                        )
                        # Emit node failed event
                        if node_state:
                            asyncio.create_task(
                                emit_agent_event(
                                    run.project_id,
                                    "agent.step.failed",
                                    node_state_data=node_state.model_dump(),
                                    error=error_msg,
                                )
                            )

            # Get final state
            final_state = await langgraph_app.ainvoke(
                {"messages": [HumanMessage(content=run.input_prompt or "")], "project_id": run.project_id}
            )

            self.update_run(
                run_id,
                output_summary=final_state["messages"][-1].content if final_state.get("messages") else None,
                status=AgentRunStatus.COMPLETED,
                finished=True,
            )
            # Event emission handled in update_run
        except Exception as e:
            import traceback

            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.update_run(run_id, output_summary=error_msg, status=AgentRunStatus.FAILED, finished=True)
            # Mark all nodes as failed
            node_state = self.update_node_state(run_id, "agent", status="failed", error=str(e), completed=True)
            # Event emission handled in update_run

    def _row_to_run(self, row) -> AgentRun:
        context_item_ids = []
        if row.get("context_item_ids_json"):
            try:
                context_item_ids = json.loads(row["context_item_ids_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return AgentRun(
            id=row["id"],
            project_id=row["project_id"],
            agent_id=row["agent_id"],
            workflow_id=row.get("workflow_id"),
            status=AgentRunStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row.get("finished_at") else None,
            input_prompt=row.get("input_prompt") or "",
            input_query=row.get("input_prompt") or "",
            output_summary=row.get("output_summary"),
            context_item_ids=context_item_ids,
        )

    def _row_to_step(self, row) -> AgentStep:
        input_data = None
        output_data = None
        if row.get("input_json"):
            try:
                input_data = json.loads(row["input_json"])
            except (json.JSONDecodeError, ValueError):
                input_data = row["input_json"]
        if row.get("output_json"):
            try:
                output_data = json.loads(row["output_json"])
            except (json.JSONDecodeError, ValueError):
                output_data = row["output_json"]

        return AgentStep(
            id=row["id"],
            run_id=row["run_id"],
            step_number=row["step_number"],
            node_id=row.get("node_id"),
            status=AgentStepStatus(row["status"]),
            input=str(input_data) if input_data else None,
            output=str(output_data) if output_data else None,
            error=row.get("error"),
            duration_ms=row.get("duration_ms"),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
        )

    def _row_to_message(self, row) -> AgentMessage:
        context_item_ids = []
        if row.get("context_item_ids_json"):
            try:
                context_item_ids = json.loads(row["context_item_ids_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return AgentMessage(
            id=row["id"],
            run_id=row["run_id"],
            role=AgentMessageRole(row["role"]),
            content=row["content"],
            context_item_ids=context_item_ids,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_node_state(self, row) -> AgentNodeState:
        messages = []
        if row.get("messages_json"):
            try:
                messages = json.loads(row["messages_json"])
            except (json.JSONDecodeError, ValueError):
                pass

        return AgentNodeState(
            run_id=row["run_id"],
            node_id=row["node_id"],
            status=row["status"],
            progress=row.get("progress", 0.0),
            messages=messages,
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            error=row.get("error"),
        )


agent_service = AgentService()

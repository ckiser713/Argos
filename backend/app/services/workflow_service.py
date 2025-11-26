from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.db import db_session
from app.domain.models import (
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowNodeState,
    WorkflowNodeStatus,
    WorkflowRun,
    WorkflowRunStatus,
)
from app.services.streaming_service import emit_workflow_event
from app.services.workflow_compiler import WorkflowGraphCompiler

logger = logging.getLogger("cortex.workflow")


class WorkflowService:
    """
    Workflow service with database persistence and LangGraph integration.
    """

    def list_graphs(self, project_id: Optional[str] = None) -> List[WorkflowGraph]:
        with db_session() as conn:
            if project_id:
                rows = conn.execute("SELECT * FROM workflow_graphs WHERE project_id = ?", (project_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM workflow_graphs").fetchall()
            return [self._row_to_graph(row) for row in rows]

    def get_graph(self, workflow_id: str, project_id: Optional[str] = None) -> Optional[WorkflowGraph]:
        with db_session() as conn:
            query = "SELECT * FROM workflow_graphs WHERE id = ?"
            params = [workflow_id]
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            row = conn.execute(query, params).fetchone()
            if row:
                return self._row_to_graph(row)
        return None

    def create_graph(self, project_id: str, graph_data: dict) -> WorkflowGraph:
        graph_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Parse nodes and edges from graph_data
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        graph = WorkflowGraph(
            id=graph_id,
            project_id=project_id,
            name=graph_data.get("name", "Untitled Workflow"),
            description=graph_data.get("description"),
            nodes=[WorkflowNode(**node) for node in nodes],
            edges=[WorkflowEdge(**edge) for edge in edges],
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO workflow_graphs
                (id, project_id, name, description, graph_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    graph.id,
                    project_id,
                    graph.name,
                    graph.description or "",
                    json.dumps(
                        {
                            "nodes": [n.model_dump() for n in graph.nodes],
                            "edges": [e.model_dump() for e in graph.edges],
                        }
                    ),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()

        return graph

    def update_graph(self, project_id: str, workflow_id: str, graph_data: dict) -> WorkflowGraph:
        now = datetime.now(timezone.utc)

        # Ensure graph exists and belongs to project
        existing = self.get_graph(workflow_id, project_id=project_id)
        if not existing:
            raise ValueError("Workflow graph not found")

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        updated_graph = WorkflowGraph(
            id=workflow_id,
            project_id=project_id,
            name=graph_data.get("name", existing.name),
            description=graph_data.get("description", existing.description),
            nodes=[WorkflowNode(**node) for node in nodes],
            edges=[WorkflowEdge(**edge) for edge in edges],
        )

        with db_session() as conn:
            conn.execute(
                """
                UPDATE workflow_graphs
                SET name = ?, description = ?, graph_json = ?, updated_at = ?
                WHERE id = ? AND project_id = ?
                """,
                (
                    updated_graph.name,
                    updated_graph.description or "",
                    json.dumps(
                        {
                            "nodes": [n.model_dump() for n in updated_graph.nodes],
                            "edges": [e.model_dump() for e in updated_graph.edges],
                        }
                    ),
                    now.isoformat(),
                    workflow_id,
                    project_id,
                ),
            )
            conn.commit()

        return updated_graph

    def list_runs(self, project_id: Optional[str] = None, workflow_id: Optional[str] = None) -> List[WorkflowRun]:
        with db_session() as conn:
            query = "SELECT * FROM workflow_runs WHERE 1=1"
            params = []

            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if workflow_id:
                query += " AND workflow_id = ?"
                params.append(workflow_id)

            query += " ORDER BY started_at DESC"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_run(row) for row in rows]

    def get_run(self, run_id: str, project_id: Optional[str] = None) -> Optional[WorkflowRun]:
        with db_session() as conn:
            query = "SELECT * FROM workflow_runs WHERE id = ?"
            params = [run_id]
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            row = conn.execute(query, params).fetchone()
            if row:
                return self._row_to_run(row)
        return None

    def create_run(
        self,
        project_id: str,
        workflow_id: str,
        input_data: Optional[dict] = None,
    ) -> WorkflowRun:
        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        run = WorkflowRun(
            id=run_id,
            project_id=project_id,
            workflow_id=workflow_id,
            status=WorkflowRunStatus.PENDING,
            started_at=now,
            finished_at=None,
            last_message="Run created (pending).",
        )

        with db_session() as conn:
            conn.execute(
                """
                INSERT INTO workflow_runs
                (id, project_id, workflow_id, status, input_json, started_at, last_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    project_id,
                    run.workflow_id,
                    run.status.value,
                    json.dumps(input_data or {}),
                    run.started_at.isoformat(),
                    run.last_message,
                ),
            )
            conn.commit()

        return run

    def update_run_status(
        self,
        run_id: str,
        status: WorkflowRunStatus,
        last_message: Optional[str] = None,
        finished: bool | None = None,
        output_data: Optional[dict] = None,
    ) -> Optional[WorkflowRun]:
        terminal_statuses = {
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLED,
        }

        with db_session() as conn:
            updates = []
            params = []

            if status:
                updates.append("status = ?")
                params.append(status.value)
            if last_message:
                updates.append("last_message = ?")
                params.append(last_message)
            if output_data:
                updates.append("output_json = ?")
                params.append(json.dumps(output_data))
            if finished or (status in terminal_statuses):
                updates.append("finished_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())

            if updates:
                params.append(run_id)
                query = f"UPDATE workflow_runs SET {', '.join(updates)} WHERE id = ?"
                conn.execute(query, params)
                conn.commit()

            row = conn.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            if row:
                updated_run = self._row_to_run(row)
                # Get project_id for event emission
                project_row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
                project_id = project_row["project_id"] if project_row else None

                # Emit event
                if project_id:
                    asyncio.create_task(
                        emit_workflow_event(
                            project_id=project_id,
                            event_type="workflow.run.updated",
                            run_data=updated_run.model_dump(),
                        )
                    )
                return updated_run
        return None

    def get_node_state(self, run_id: str, node_id: str) -> Optional[WorkflowNodeState]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_node_states WHERE run_id = ? AND node_id = ?", (run_id, node_id)
            ).fetchone()
            if row:
                return self._row_to_node_state(row)
        return None

    def set_node_state(
        self,
        run_id: str,
        node_id: str,
        *,
        status: WorkflowNodeStatus,
        progress: float = 0.0,
        messages: Optional[List[str]] = None,
        error: Optional[str] = None,
        started: bool = False,
        completed: bool = False,
    ) -> WorkflowNodeState:
        now = datetime.now(timezone.utc)

        with db_session() as conn:
            # Check if exists
            existing = conn.execute(
                "SELECT * FROM workflow_node_states WHERE run_id = ? AND node_id = ?", (run_id, node_id)
            ).fetchone()

            if existing:
                updates = []
                params = []

                if status:
                    updates.append("status = ?")
                    params.append(status.value)
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
                    query = f"UPDATE workflow_node_states SET {', '.join(updates)} WHERE run_id = ? AND node_id = ?"
                    conn.execute(query, params)
            else:
                conn.execute(
                    """
                    INSERT INTO workflow_node_states
                    (run_id, node_id, status, progress, messages_json, started_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        node_id,
                        status.value,
                        progress,
                        json.dumps(messages or []),
                        now.isoformat() if started else None,
                    ),
                )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM workflow_node_states WHERE run_id = ? AND node_id = ?", (run_id, node_id)
            ).fetchone()
            node_state = self._row_to_node_state(row)

            # Emit event
            run = self.get_run(run_id)
            if run:
                # Get project_id
                project_row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
                project_id = project_row["project_id"] if project_row else None

                if project_id:
                    asyncio.create_task(
                        emit_workflow_event(
                            project_id=project_id,
                            event_type="workflow.node_state.updated",
                            node_state_data=node_state.model_dump(),
                        )
                    )

            return node_state

    def list_node_states(self, run_id: str) -> List[WorkflowNodeState]:
        with db_session() as conn:
            rows = conn.execute("SELECT * FROM workflow_node_states WHERE run_id = ?", (run_id,)).fetchall()
            return [self._row_to_node_state(row) for row in rows]

    async def execute_workflow_run(self, run_id: str):
        """Execute a workflow run using LangGraph."""
        run = self.get_run(run_id)
        if not run:
            logger.error(f"Workflow run {run_id} not found")
            return

        workflow_graph = self.get_graph(run.workflow_id, project_id=run.project_id)
        if not workflow_graph:
            self.update_run_status(run_id, WorkflowRunStatus.FAILED, last_message="Workflow graph not found")
            return

        # Get project_id from run
        with db_session() as conn:
            row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            project_id = row["project_id"] if row else None

        if not project_id:
            self.update_run_status(run_id, WorkflowRunStatus.FAILED, last_message="Project ID not found")
            return

        # Update run status
        self.update_run_status(run_id, WorkflowRunStatus.RUNNING, last_message="Starting workflow execution")

        # Emit run started event
        asyncio.create_task(
            emit_workflow_event(
                project_id=project_id,
                event_type="workflow.run.created",
                run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
            )
        )

        try:
            # Compile graph with workflow service reference for node state tracking
            compiler = WorkflowGraphCompiler(workflow_service=self)
            compiled_graph = compiler.compile(workflow_graph)

            # Get input data
            with db_session() as conn:
                row = conn.execute("SELECT input_json FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
                input_data = json.loads(row["input_json"]) if row and row.get("input_json") else {}

            # Prepare initial state
            initial_state = {
                "run_id": run_id,
                "project_id": project_id,
                "input": input_data,
                "output": {},
                "messages": [],
                "current_node": None,
            }

            # Execute graph
            async for event in compiled_graph.astream_events(initial_state, version="v1"):
                # Handle events
                await self._handle_execution_event(run_id, project_id, event)

            # Update run status to completed
            final_state = await compiled_graph.ainvoke(initial_state)
            self.update_run_status(
                run_id,
                WorkflowRunStatus.COMPLETED,
                last_message="Workflow execution completed",
                finished=True,
                output_data=final_state.get("output", {}),
            )

            # Emit completion event
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.completed",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )

        except asyncio.CancelledError:
            # Handle cancellation
            self.update_run_status(
                run_id, WorkflowRunStatus.CANCELLED, last_message="Workflow execution cancelled", finished=True
            )
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.cancelled",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )
        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            self.update_run_status(
                run_id, WorkflowRunStatus.FAILED, last_message=f"Workflow execution failed: {str(e)}", finished=True
            )
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.failed",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )

    async def _handle_execution_event(self, run_id: str, project_id: str, event: dict):
        """Handle LangGraph execution events."""
        event_type = event.get("event")
        name = event.get("name", "")

        if event_type == "on_chain_start":
            # Node started
            self.set_node_state(run_id, name, status=WorkflowNodeStatus.RUNNING, progress=0.0, started=True)
            # Emit WebSocket event
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.node.started",
                    node_state_data={"node_id": name, "run_id": run_id},
                )
            )

        elif event_type == "on_chain_end":
            # Node completed
            output = event.get("data", {}).get("output")
            self.set_node_state(
                run_id,
                name,
                status=WorkflowNodeStatus.COMPLETED,
                progress=1.0,
                completed=True,
                messages=[str(output)] if output else [],
            )
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.node.completed",
                    node_state_data={"node_id": name, "run_id": run_id},
                )
            )

        elif event_type == "on_chain_error":
            # Node failed
            error = event.get("error", "Unknown error")
            self.set_node_state(run_id, name, status=WorkflowNodeStatus.FAILED, completed=True, error=str(error))
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.node.failed",
                    node_state_data={"node_id": name, "run_id": run_id, "error": str(error)},
                )
            )

    async def cancel_workflow_run(self, run_id: str) -> WorkflowRun:
        """Cancel a running workflow."""
        run = self.get_run(run_id)
        if not run:
            raise ValueError("Workflow run not found")

        if run.status not in [WorkflowRunStatus.PENDING, WorkflowRunStatus.RUNNING]:
            raise ValueError(f"Cannot cancel run with status: {run.status}")

        # Get project_id
        with db_session() as conn:
            row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            project_id = row["project_id"] if row else None

        # Update status
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, cancelled_at = ?, finished_at = ?, last_message = ?
                WHERE id = ?
                """,
                (
                    WorkflowRunStatus.CANCELLED.value,
                    now.isoformat(),
                    now.isoformat(),
                    "Workflow execution cancelled",
                    run_id,
                ),
            )
            conn.commit()

        # Cancel all running nodes
        node_states = self.list_node_states(run_id)
        for node_state in node_states:
            if node_state.status == WorkflowNodeStatus.RUNNING:
                self.set_node_state(run_id, node_state.node_id, status=WorkflowNodeStatus.CANCELLED, completed=True)

        # Emit cancellation event
        if project_id:
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.cancelled",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )

        return self.get_run(run_id)

    async def pause_workflow_run(self, run_id: str, checkpoint_data: Optional[dict] = None) -> WorkflowRun:
        """Pause a running workflow (checkpoint state)."""
        run = self.get_run(run_id)
        if not run:
            raise ValueError("Workflow run not found")

        if run.status != WorkflowRunStatus.RUNNING:
            raise ValueError(f"Cannot pause run with status: {run.status}")

        # Get project_id
        with db_session() as conn:
            row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            project_id = row["project_id"] if row else None

        # Update status
        now = datetime.now(timezone.utc)
        with db_session() as conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, paused_at = ?, checkpoint_json = ?
                WHERE id = ?
                """,
                (WorkflowRunStatus.PAUSED.value, now.isoformat(), json.dumps(checkpoint_data or {}), run_id),
            )
            conn.commit()

        # Emit pause event
        if project_id:
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.paused",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )

        return self.get_run(run_id)

    async def resume_workflow_run(self, run_id: str) -> WorkflowRun:
        """Resume a paused workflow from checkpoint."""
        run = self.get_run(run_id)
        if not run:
            raise ValueError("Workflow run not found")

        if run.status != WorkflowRunStatus.PAUSED:
            raise ValueError(f"Cannot resume run with status: {run.status}")

        # Get project_id
        with db_session() as conn:
            row = conn.execute("SELECT project_id FROM workflow_runs WHERE id = ?", (run_id,)).fetchone()
            project_id = row["project_id"] if row else None

        # Update status
        with db_session() as conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, paused_at = NULL
                WHERE id = ?
                """,
                (WorkflowRunStatus.RUNNING.value, run_id),
            )
            conn.commit()

        # Resume execution
        asyncio.create_task(self.execute_workflow_run(run_id))

        # Emit resume event
        if project_id:
            asyncio.create_task(
                emit_workflow_event(
                    project_id=project_id,
                    event_type="workflow.run.resumed",
                    run_data=self.get_run(run_id).model_dump() if self.get_run(run_id) else {},
                )
            )

        return self.get_run(run_id)

    def get_execution_status(self, run_id: str) -> dict:
        """Get current execution status and progress."""
        run = self.get_run(run_id)
        if not run:
            raise ValueError("Workflow run not found")

        node_states = self.list_node_states(run_id)

        # Calculate overall progress
        total_progress = 0.0
        if node_states:
            total_progress = sum(node.progress for node in node_states) / len(node_states)

        # Find current running node
        current_node = None
        for node_state in node_states:
            if node_state.status == WorkflowNodeStatus.RUNNING:
                current_node = node_state.node_id
                break

        return {
            "run_id": run_id,
            "status": run.status.value,
            "progress": total_progress,
            "current_node": current_node,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "node_states": [ns.model_dump() for ns in node_states],
        }

    def _row_to_graph(self, row) -> WorkflowGraph:
        graph_data = json.loads(row["graph_json"])
        return WorkflowGraph(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"],
            nodes=[WorkflowNode(**node) for node in graph_data.get("nodes", [])],
            edges=[WorkflowEdge(**edge) for edge in graph_data.get("edges", [])],
        )

    def _row_to_run(self, row) -> WorkflowRun:
        return WorkflowRun(
            id=row["id"],
            project_id=row["project_id"],
            workflow_id=row["workflow_id"],
            status=WorkflowRunStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if "finished_at" in row.keys() and row["finished_at"] else None,
            last_message=row["last_message"] if "last_message" in row.keys() else None,
            task_id=row["task_id"] if "task_id" in row.keys() else None,
            paused_at=datetime.fromisoformat(row["paused_at"]) if "paused_at" in row.keys() and row["paused_at"] else None,
            cancelled_at=datetime.fromisoformat(row["cancelled_at"]) if "cancelled_at" in row.keys() and row["cancelled_at"] else None,
        )

    def _row_to_node_state(self, row) -> WorkflowNodeState:
        messages: List[str] = []
        if row.get("messages_json"):
            try:
                loaded = json.loads(row["messages_json"])
                if isinstance(loaded, list):
                    messages = [str(m) for m in loaded]
            except (json.JSONDecodeError, ValueError, TypeError):
                messages = []

        return WorkflowNodeState(
            node_id=row["node_id"],
            status=WorkflowNodeStatus(row["status"]),
            progress=row.get("progress", 0.0),
            messages=messages,
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            error=row.get("error"),
        )


workflow_service = WorkflowService()

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from app.domain.models import (
    WorkflowGraph,
    WorkflowNode,
    WorkflowEdge,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowNodeState,
    WorkflowNodeStatus,
)


class WorkflowService:
    """
    In-memory workflow graph and runs.

    The default graph mirrors the ReactFlow mock in the current frontend.
    """

    def __init__(self) -> None:
        self._graphs: Dict[str, WorkflowGraph] = {}
        self._runs: Dict[str, WorkflowRun] = {}
        self._run_node_states: Dict[str, Dict[str, WorkflowNodeState]] = {}

        default_graph = WorkflowGraph(
            id="default_retrieval_graph",
            name="Default Retrieval Workflow",
            description="Start -> retrieve_docs -> grade_documents -> generate_answer (+web_search_tool branch) -> end",
            nodes=[
                WorkflowNode(id="start", label="__start__", x=250, y=0),
                WorkflowNode(id="retrieve", label="retrieve_docs", x=250, y=100),
                WorkflowNode(id="grade", label="grade_documents", x=250, y=200),
                WorkflowNode(id="generate", label="generate_answer", x=0, y=300),
                WorkflowNode(id="web_search", label="web_search_tool", x=500, y=300),
                WorkflowNode(id="finalize", label="__end__", x=250, y=450),
            ],
            edges=[
                WorkflowEdge(id="e1", source="start", target="retrieve"),
                WorkflowEdge(id="e2", source="retrieve", target="grade"),
                WorkflowEdge(id="e3", source="grade", target="generate"),
                WorkflowEdge(id="e4", source="grade", target="web_search"),
                WorkflowEdge(id="e5", source="web_search", target="generate"),
                WorkflowEdge(id="e6", source="generate", target="finalize"),
            ],
        )

        self._graphs[default_graph.id] = default_graph

    # --- Graphs ---

    def list_graphs(self) -> List[WorkflowGraph]:
        return list(self._graphs.values())

    def get_graph(self, workflow_id: str) -> Optional[WorkflowGraph]:
        return self._graphs.get(workflow_id)

    # --- Runs ---

    def list_runs(self) -> List[WorkflowRun]:
        return list(self._runs.values())

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        return self._runs.get(run_id)

    def create_run(self, workflow_id: str) -> WorkflowRun:
        now = datetime.utcnow()
        run_id = f"run_{len(self._runs) + 1}"
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow_id,
            status=WorkflowRunStatus.PENDING,
            started_at=now,
            finished_at=None,
            last_message="Run created (pending).",
        )
        self._runs[run.id] = run

        graph = self._graphs[workflow_id]
        self._run_node_states[run.id] = {
            node.id: WorkflowNodeState(
                node_id=node.id,
                status=WorkflowNodeStatus.IDLE,
                progress=0.0,
            )
            for node in graph.nodes
        }
        return run

    def update_run_status(
        self,
        run_id: str,
        status: WorkflowRunStatus,
        last_message: Optional[str] = None,
        finished: bool | None = None,
    ) -> Optional[WorkflowRun]:
        run = self._runs.get(run_id)
        if not run:
            return None

        data = run.model_dump()
        data["status"] = status
        if last_message is not None:
            data["last_message"] = last_message
        if finished:
            data["finished_at"] = datetime.utcnow()

        updated = WorkflowRun(**data)
        self._runs[run_id] = updated
        return updated

    # --- Node state helpers for streaming ---

    def get_node_state(self, run_id: str, node_id: str) -> Optional[WorkflowNodeState]:
        return self._run_node_states.get(run_id, {}).get(node_id)

    def set_node_state(
        self,
        run_id: str,
        node_id: str,
        *,
        status: WorkflowNodeStatus,
        progress: float,
    ) -> Optional[WorkflowNodeState]:
        nodes = self._run_node_states.get(run_id)
        if nodes is None:
            return None

        current = nodes.get(node_id)
        if current is None:
            current = WorkflowNodeState(node_id=node_id, status=status, progress=progress)

        updated = WorkflowNodeState(
            node_id=current.node_id,
            status=status,
            progress=progress,
        )
        nodes[node_id] = updated
        return updated

    def list_node_states(self, run_id: str) -> List[WorkflowNodeState]:
        return list(self._run_node_states.get(run_id, {}).values())


workflow_service = WorkflowService()

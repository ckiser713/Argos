import asyncio
import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.domain.models import (
    IngestJobEvent,
    IngestJobEventType,
    AgentRunEvent,
    AgentRunEventType,
    WorkflowNodeEvent,
    WorkflowNodeEventType,
    WorkflowNodeStatus,
    IngestStatus, # Added for enum usage
    AgentRunStatus, # Added for enum usage
    WorkflowRunStatus, # Added for enum usage
)
from app.services.ingest_service import ingest_service
from app.services.agent_service import agent_service
from app.services.workflow_service import workflow_service

logger = logging.getLogger("cortex.streaming")

router = APIRouter()


async def _send_json(websocket: WebSocket, payload) -> None:
    await websocket.send_text(payload if isinstance(payload, str) else json.dumps(payload))


# --- Ingest job streaming ---


@router.websocket("/ingest/{job_id}")
async def stream_ingest_job(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    logger.info("ingest_stream_connected", extra={"job_id": job_id})

    job = ingest_service.get_job(job_id)
    if not job:
        logger.warning("ingest_job_not_found", extra={"job_id": job_id})
        await _send_json(
            websocket,
            {"error": "job_not_found", "job_id": job_id},
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Deterministic 4-step state machine: QUEUED -> RUNNING (0.3) -> RUNNING (0.7) -> COMPLETED (1.0)
        steps: List[tuple[IngestJobEventType, float, str]] = [
            (IngestJobEventType.QUEUED, 0.0, "Job queued (stub)."),
            (IngestJobEventType.RUNNING, 0.3, "Ingest in progress (stage 1/3)."),
            (IngestJobEventType.RUNNING, 0.7, "Ingest in progress (stage 2/3)."),
            (IngestJobEventType.COMPLETED, 1.0, "Ingest completed (stub)."),
        ]

        for event_type, progress, message in steps:
            # Map event_type to IngestStatus
            new_status = None
            if event_type == IngestJobEventType.QUEUED:
                new_status = IngestStatus.QUEUED
            elif event_type == IngestJobEventType.RUNNING:
                new_status = IngestStatus.RUNNING
            elif event_type == IngestJobEventType.COMPLETED:
                new_status = IngestStatus.COMPLETED
            elif event_type == IngestJobEventType.FAILED: # Although not used in this stub, for completeness
                new_status = IngestStatus.FAILED

            job = ingest_service.update_job(
                job_id,
                status=new_status,
                progress=progress,
                message=message,
            )
            if not job:
                break

            event = IngestJobEvent(event_type=event_type, job=job)
            await _send_json(websocket, event.model_dump())
            await asyncio.sleep(0.75)

    except WebSocketDisconnect:
        logger.info("ingest_stream_disconnected", extra={"job_id": job_id})
    except Exception as exc:
        logger.exception("ingest_stream_error", extra={"job_id": job_id})
        try:
            await _send_json(
                websocket,
                {"error": "stream_error", "message": str(exc), "job_id": job_id},
            )
        finally:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# --- Agent run streaming ---


@router.websocket("/agents/{run_id}")
async def stream_agent_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    logger.info("agent_stream_connected", extra={"run_id": run_id})

    run = agent_service.get_run(run_id)
    if not run:
        logger.warning("agent_run_not_found", extra={"run_id": run_id})
        await _send_json(websocket, {"error": "run_not_found", "run_id": run_id})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Deterministic 3-step: PENDING -> RUNNING -> COMPLETED
        async def emit(event_type: AgentRunEventType, summary: str | None, finished: bool) -> None:
            # Map event_type to AgentRunStatus
            new_status = None
            if event_type == AgentRunEventType.PENDING:
                new_status = AgentRunStatus.PENDING
            elif event_type == AgentRunEventType.RUNNING:
                new_status = AgentRunStatus.RUNNING
            elif event_type == AgentRunEventType.COMPLETED:
                new_status = AgentRunStatus.COMPLETED
            elif event_type == AgentRunEventType.FAILED: # Although not used in this stub, for completeness
                new_status = AgentRunStatus.FAILED

            updated = agent_service.update_run(
                run_id,
                status=new_status,
                output_summary=summary,
                finished=finished,
            )
            if not updated:
                return
            await _send_json(websocket, AgentRunEvent(event_type=event_type, run=updated).model_dump())

        await emit(AgentRunEventType.PENDING, None, False)
        await asyncio.sleep(0.5)

        await emit(AgentRunEventType.RUNNING, "Stubbed agent run executing (no real model calls).", False)
        await asyncio.sleep(1.0)

        await emit(
            AgentRunEventType.COMPLETED,
            "Stubbed agent run completed successfully.",
            True,
        )

    except WebSocketDisconnect:
        logger.info("agent_stream_disconnected", extra={"run_id": run_id})
    except Exception as exc:
        logger.exception("agent_stream_error", extra={"run_id": run_id})
        try:
            await _send_json(
                websocket,
                {"error": "stream_error", "message": str(exc), "run_id": run_id},
            )
        finally:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


# --- Workflow node streaming ---


@router.websocket("/workflows/{run_id}")
async def stream_workflow_nodes(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    logger.info("workflow_stream_connected", extra={"run_id": run_id})

    run = workflow_service.get_run(run_id)
    if not run:
        logger.warning("workflow_run_not_found", extra={"run_id": run_id})
        await _send_json(websocket, {"error": "run_not_found", "run_id": run_id})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    graph = workflow_service.get_graph(run.workflow_id)
    if not graph:
        logger.warning(
            "workflow_graph_not_found",
            extra={"run_id": run_id, "workflow_id": run.workflow_id},
        )
        await _send_json(websocket, {"error": "workflow_not_found", "run_id": run_id})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        # Deterministic node traversal along the main path
        path_ids = ["start", "retrieve", "grade", "generate", "finalize"]
        step_delay = 0.7

        async def emit_node_event(node_id: str, event_type: WorkflowNodeEventType, status: WorkflowNodeStatus, progress: float) -> None:
            state = workflow_service.set_node_state(
                run_id,
                node_id,
                status=status,
                progress=progress,
            )
            if state is None:
                return
            event = WorkflowNodeEvent(
                event_type=event_type,
                run_id=run_id,
                node_id=node_id,
                state=state,
            )
            await _send_json(websocket, event.model_dump())

        # Mark run as RUNNING
        workflow_service.update_run_status(
            run_id,
            status=WorkflowRunStatus.RUNNING,
            last_message="Workflow execution started (stub).",
        )

        for node_id in path_ids:
            # Node started
            await emit_node_event(
                node_id=node_id,
                event_type=WorkflowNodeEventType.NODE_STARTED,
                status=WorkflowNodeStatus.RUNNING,
                progress=0.0,
            )
            await asyncio.sleep(step_delay)

            # Node progress mid
            await emit_node_event(
                node_id=node_id,
                event_type=WorkflowNodeEventType.NODE_PROGRESS,
                status=WorkflowNodeStatus.RUNNING,
                progress=0.5,
            )
            await asyncio.sleep(step_delay)

            # Node completed
            await emit_node_event(
                node_id=node_id,
                event_type=WorkflowNodeEventType.NODE_COMPLETED,
                status=WorkflowNodeStatus.COMPLETED,
                progress=1.0,
            )
            await asyncio.sleep(step_delay)

        # Mark run as COMPLETED
        workflow_service.update_run_status(
            run_id,
            status=WorkflowRunStatus.COMPLETED,
            last_message="Workflow completed successfully (stub).",
            finished=True,
        )

    except WebSocketDisconnect:
        logger.info("workflow_stream_disconnected", extra={"run_id": run_id})
    except Exception as exc:
        logger.exception("workflow_stream_error", extra={"run_id": run_id})
        try:
            await _send_json(
                websocket,
                {"error": "stream_error", "message": str(exc), "run_id": run_id},
            )
        finally:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

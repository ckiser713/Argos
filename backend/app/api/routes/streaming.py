from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from app.services.agent_service import agent_service
from app.services.ingest_service import ingest_service
from app.services.workflow_service import workflow_service
from app.services.streaming_service import connection_manager
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

logger = logging.getLogger("cortex.streaming")

router = APIRouter()


def _json_default(obj: object) -> str:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)


async def _send_json(websocket: WebSocket, payload) -> None:
    """Helper to send JSON over WebSocket."""
    if isinstance(payload, str):
        await websocket.send_text(payload)
    else:
        await websocket.send_text(json.dumps(payload, default=_json_default))


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    """Keep connection open until client disconnects."""
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("websocket_receive_error", extra={"error": str(exc)})


# --- Ingest job streaming ---


@router.websocket("/projects/{project_id}/ingest/{job_id}")
async def stream_ingest_job(websocket: WebSocket, project_id: str, job_id: str) -> None:
    """WebSocket endpoint for streaming ingest job events."""
    connected = await connection_manager.connect(websocket, project_id)
    if not connected:
        return
    logger.info("ingest_stream_connected", extra={"job_id": job_id, "project_id": project_id})

    job = ingest_service.get_job(job_id)
    if not job or job.project_id != project_id:
        logger.warning("ingest_job_not_found", extra={"job_id": job_id, "project_id": project_id})
        await _send_json(
            websocket,
            {"error": "job_not_found", "job_id": job_id},
        )
        await websocket.close(code=1008)
        await connection_manager.disconnect(websocket, project_id)
        return

    try:
        # Send initial state
        await _send_json(websocket, {"type": "ingest.job.created", "job": job.model_dump()})
        # Rely on event broadcasts; keep socket alive until client disconnects
        await _wait_for_disconnect(websocket)

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
            await websocket.close(code=1011)
    finally:
        await connection_manager.disconnect(websocket, project_id)


@router.get("/projects/{project_id}/ingest/{job_id}/events")
async def stream_ingest_job_sse(project_id: str, job_id: str):
    """SSE endpoint for streaming ingest job events."""
    job = ingest_service.get_job(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest job not found")

    async def event_generator():
        yield "event: ingest.job.created\n"
        yield f"data: {json.dumps({'type': 'ingest.job.created', 'job': job.model_dump()})}\n\n"

        last_status = job.status
        while True:
            await asyncio.sleep(1.0)

            updated_job = ingest_service.get_job(job_id)
            if not updated_job:
                break

            if updated_job.status != last_status or updated_job.progress != job.progress:
                event_type = f"ingest.job.{updated_job.status.value}"
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps({'type': event_type, 'job': updated_job.model_dump()})}\n\n"

                if updated_job.status.value in ["completed", "failed", "cancelled"]:
                    break

                last_status = updated_job.status

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# --- Agent run streaming ---


@router.websocket("/projects/{project_id}/agent-runs/{run_id}")
async def stream_agent_run(websocket: WebSocket, project_id: str, run_id: str) -> None:
    """WebSocket endpoint for streaming agent run events."""
    connected = await connection_manager.connect(websocket, project_id)
    if not connected:
        return
    logger.info("agent_stream_connected", extra={"run_id": run_id, "project_id": project_id})

    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        logger.warning("agent_run_not_found", extra={"run_id": run_id, "project_id": project_id})
        await _send_json(websocket, {"error": "run_not_found", "run_id": run_id})
        await websocket.close(code=1008)
        await connection_manager.disconnect(websocket, project_id)
        return

    try:
        # Send initial state
        await _send_json(websocket, {"type": "agent.run.created", "run": run.model_dump()})
        # Rely on event broadcasts; keep socket alive until client disconnects
        await _wait_for_disconnect(websocket)

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
            await websocket.close(code=1011)
    finally:
        await connection_manager.disconnect(websocket, project_id)


# --- Workflow node streaming ---


@router.websocket("/projects/{project_id}/workflows/{run_id}")
async def stream_workflow_nodes(websocket: WebSocket, project_id: str, run_id: str) -> None:
    """WebSocket endpoint for streaming workflow node events."""
    connected = await connection_manager.connect(websocket, project_id)
    if not connected:
        return
    logger.info("workflow_stream_connected", extra={"run_id": run_id, "project_id": project_id})

    run = workflow_service.get_run(run_id)
    if not run or run.project_id != project_id:
        logger.warning("workflow_run_not_found", extra={"run_id": run_id})
        await _send_json(websocket, {"error": "run_not_found", "run_id": run_id})
        await websocket.close(code=1008)
        await connection_manager.disconnect(websocket, project_id)
        return

    try:
        await _send_json(websocket, {"type": "workflow.run.created", "run": run.model_dump()})
        # Rely on event broadcasts; keep socket alive until client disconnects
        await _wait_for_disconnect(websocket)

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
            await websocket.close(code=1011)
    finally:
        await connection_manager.disconnect(websocket, project_id)

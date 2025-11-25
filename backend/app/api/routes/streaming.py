from __future__ import annotations

import asyncio
import json
import logging

from app.services.agent_service import agent_service
from app.services.ingest_service import ingest_service
from app.services.streaming_service import connection_manager
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

logger = logging.getLogger("cortex.streaming")

router = APIRouter()


async def _send_json(websocket: WebSocket, payload) -> None:
    """Helper to send JSON over WebSocket."""
    await websocket.send_text(payload if isinstance(payload, str) else json.dumps(payload))


# --- Ingest job streaming ---


@router.websocket("/projects/{project_id}/ingest/{job_id}")
async def stream_ingest_job(websocket: WebSocket, project_id: str, job_id: str) -> None:
    """WebSocket endpoint for streaming ingest job events."""
    await connection_manager.connect(websocket, project_id)
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

        # Poll for updates (in production, this would be event-driven)
        last_status = job.status
        while True:
            await asyncio.sleep(1.0)  # Poll every second

            updated_job = ingest_service.get_job(job_id)
            if not updated_job:
                break

            # Send update if status changed
            if updated_job.status != last_status or updated_job.progress != job.progress:
                event_type = f"ingest.job.{updated_job.status.value}"
                await _send_json(websocket, {"type": event_type, "job": updated_job.model_dump()})

                if updated_job.status.value in ["completed", "failed", "cancelled"]:
                    break

                last_status = updated_job.status
                job = updated_job

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
    await connection_manager.connect(websocket, project_id)
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

        # Poll for updates (in production, this would be event-driven)
        last_status = run.status
        while True:
            await asyncio.sleep(1.0)

            updated_run = agent_service.get_run(run_id)
            if not updated_run:
                break

            # Send run updates
            if updated_run.status != last_status:
                event_type = f"agent.run.{updated_run.status.value}"
                await _send_json(websocket, {"type": event_type, "run": updated_run.model_dump()})

                if updated_run.status.value in ["completed", "failed", "cancelled"]:
                    break

                last_status = updated_run.status

            # Send step updates
            steps_response = agent_service.list_steps(run_id, limit=100)
            if steps_response.items:
                for step in steps_response.items[-5:]:  # Last 5 steps
                    await _send_json(websocket, {"type": "agent.step.updated", "step": step.model_dump()})

            # Send message updates
            messages_response = agent_service.list_messages(run_id, limit=100)
            if messages_response.items:
                for message in messages_response.items[-5:]:  # Last 5 messages
                    await _send_json(websocket, {"type": "agent.message.appended", "message": message.model_dump()})

            # Send node state updates
            node_states = agent_service.list_node_states(run_id)
            for node_state in node_states:
                await _send_json(
                    websocket, {"type": "workflow.node_state.updated", "nodeState": node_state.model_dump()}
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
            await websocket.close(code=1011)
    finally:
        await connection_manager.disconnect(websocket, project_id)


# --- Workflow node streaming ---


@router.websocket("/projects/{project_id}/workflows/{run_id}")
async def stream_workflow_nodes(websocket: WebSocket, project_id: str, run_id: str) -> None:
    """WebSocket endpoint for streaming workflow node events."""
    await connection_manager.connect(websocket, project_id)
    logger.info("workflow_stream_connected", extra={"run_id": run_id, "project_id": project_id})

    # Note: workflow_service would need to be implemented
    # For now, we'll use agent node states as a proxy
    run = agent_service.get_run(run_id)
    if not run or run.project_id != project_id:
        logger.warning("workflow_run_not_found", extra={"run_id": run_id})
        await _send_json(websocket, {"error": "run_not_found", "run_id": run_id})
        await websocket.close(code=1008)
        await connection_manager.disconnect(websocket, project_id)
        return

    try:
        # Poll for node state updates
        while True:
            await asyncio.sleep(1.0)

            node_states = agent_service.list_node_states(run_id)
            for node_state in node_states:
                await _send_json(
                    websocket, {"type": "workflow.node_state.updated", "nodeState": node_state.model_dump()}
                )

            # Check if run is complete
            updated_run = agent_service.get_run(run_id)
            if updated_run and updated_run.status.value in ["completed", "failed", "cancelled"]:
                await _send_json(websocket, {"type": "workflow.run.updated", "run": updated_run.model_dump()})
                break

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

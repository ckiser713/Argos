from __future__ import annotations

import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger("argos.streaming")


class ConnectionManager:
    """Manages WebSocket connections for real-time event streaming."""

    def __init__(self):
        # project_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self.max_connections_per_project = 100
        self.send_timeout_seconds = 2.0

    async def connect(self, websocket: WebSocket, project_id: str):
        """Add a WebSocket connection for a project."""
        await websocket.accept()
        async with self._lock:
            existing = self.active_connections.get(project_id, set())
            if len(existing) >= self.max_connections_per_project:
                await websocket.send_json({"error": "too_many_connections"})
                await websocket.close(code=1013)
                return False
            if project_id not in self.active_connections:
                self.active_connections[project_id] = set()
            self.active_connections[project_id].add(websocket)
        logger.info(f"WebSocket connected for project {project_id}")
        return True

    async def disconnect(self, websocket: WebSocket, project_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if project_id in self.active_connections:
                self.active_connections[project_id].discard(websocket)
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
        logger.info(f"WebSocket disconnected for project {project_id}")

    async def broadcast(self, project_id: str, event: dict):
        """Broadcast an event to all connections for a project."""
        async with self._lock:
            if project_id not in self.active_connections:
                return

            disconnected = set()
            for connection in self.active_connections[project_id]:
                try:
                    await asyncio.wait_for(connection.send_json(event), timeout=self.send_timeout_seconds)
                except Exception as e:
                    logger.warning(f"Failed to send event to connection: {e}")
                    disconnected.add(connection)

            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[project_id].discard(conn)

    async def send_to_connection(self, websocket: WebSocket, event: dict):
        """Send an event to a specific connection."""
        try:
            await websocket.send_json(event)
        except Exception as e:
            logger.warning(f"Failed to send event: {e}")
            raise


# Global connection manager instance
connection_manager = ConnectionManager()


async def emit_ingest_event(project_id: str, event_type: str, job_data: dict, error: str = None):
    """Emit an ingest job event."""
    from datetime import datetime, timezone

    event = {
        "type": event_type,
        "job": job_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        event["errorMessage"] = error
    await connection_manager.broadcast(project_id, event)


async def emit_agent_event(
    project_id: str,
    event_type: str,
    run_data: dict = None,
    step_data: dict = None,
    message_data: dict = None,
    node_state_data: dict = None,
    error: str = None,
):
    """Emit an agent run event."""
    from datetime import datetime, timezone

    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if run_data:
        event["run"] = run_data
    if step_data:
        event["step"] = step_data
    if message_data:
        event["message"] = message_data
    if node_state_data:
        event["nodeState"] = node_state_data
    if error:
        event["errorMessage"] = error
    await connection_manager.broadcast(project_id, event)


async def emit_workflow_event(project_id: str, event_type: str, run_data: dict = None, node_state_data: dict = None):
    """Emit a workflow event."""
    from datetime import datetime, timezone

    event = {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if run_data:
        event["run"] = run_data
    if node_state_data:
        event["nodeState"] = node_state_data
    await connection_manager.broadcast(project_id, event)

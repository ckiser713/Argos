from __future__ import annotations

from datetime import datetime

from app.domain.models import SystemStatus, SystemStatusLevel


class SystemService:
    """
    Simple system status stub.
    """

    def get_status(self) -> SystemStatus:
        # A deterministic, static stub. You can wire in real metrics later.
        return SystemStatus(
            status=SystemStatusLevel.NOMINAL,
            message="Cortex backend stub is running.",
            timestamp=datetime.utcnow(),
        )


system_service = SystemService()

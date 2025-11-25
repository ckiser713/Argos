from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Protocol, Sequence

from app.domain.gap_analysis import GapReport


class GapAnalysisRepo(Protocol):
    async def save_gap_report(self, report: GapReport) -> None:
        ...

    async def get_latest_gap_report(self, project_id: str) -> Optional[GapReport]:
        ...

    async def list_gap_reports(self, project_id: str, limit: int = 20) -> Sequence[GapReport]:
        ...


class InMemoryGapAnalysisRepo(GapAnalysisRepo):
    """
    Simple in-memory implementation suitable for initial wiring and tests.

    This stores reports per project in insertion order and returns them ordered
    from newest to oldest for listing.
    """

    def __init__(self) -> None:
        self._reports_by_project: Dict[str, List[GapReport]] = defaultdict(list)

    async def save_gap_report(self, report: GapReport) -> None:
        reports = self._reports_by_project[report.project_id]
        reports.append(report)
        # Keep newest first
        reports.sort(key=lambda r: r.generated_at, reverse=True)

    async def get_latest_gap_report(self, project_id: str) -> Optional[GapReport]:
        reports = self._reports_by_project.get(project_id)
        if not reports:
            return None
        return reports[0]

    async def list_gap_reports(self, project_id: str, limit: int = 20) -> Sequence[GapReport]:
        reports = self._reports_by_project.get(project_id, [])
        return reports[: max(0, limit)]


# Default singleton repo instance and accessor for FastAPI dependency injection.

_default_repo: InMemoryGapAnalysisRepo = InMemoryGapAnalysisRepo()


def get_gap_analysis_repo() -> GapAnalysisRepo:
    return _default_repo

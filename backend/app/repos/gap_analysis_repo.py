from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Protocol, Sequence

from app.db import db_session
from app.domain.gap_analysis import GapReport, GapSuggestion

logger = logging.getLogger(__name__)


class GapAnalysisRepo(Protocol):
    async def save_gap_report(self, report: GapReport) -> None: ...

    async def get_latest_gap_report(self, project_id: str) -> Optional[GapReport]: ...

    async def list_gap_reports(self, project_id: str, limit: int = 20) -> Sequence[GapReport]: ...


class SqliteGapAnalysisRepo(GapAnalysisRepo):
    """
    Production-ready SQLite implementation.
    """

    async def save_gap_report(self, report: GapReport) -> None:
        # Generate a Report ID if one isn't implicit (GapReport model doesn't have an ID,
        # so we usually derive it or generate it here to link suggestions).
        # Since the domain model GapReport doesn't have an ID field, we'll generate one
        # for the DB relationship but we can't store it on the model unless we update the model.
        # Strategy: Use a UUID for the DB row.
        report_id = str(uuid.uuid4())

        with db_session() as conn:
            # 1. Save Report Header
            conn.execute(
                """
                INSERT INTO gap_reports (id, project_id, generated_at)
                VALUES (?, ?, ?)
                """,
                (
                    report_id,
                    report.project_id,
                    report.generated_at.isoformat(),
                ),
            )

            # 2. Save Suggestions
            for suggestion in report.suggestions:
                conn.execute(
                    """
                    INSERT INTO gap_suggestions
                    (id, report_id, project_id, ticket_id, status, notes, confidence, related_files_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        suggestion.id,
                        report_id,
                        suggestion.project_id,
                        suggestion.ticket_id,
                        suggestion.status,
                        suggestion.notes,
                        suggestion.confidence,
                        json.dumps(suggestion.related_files),
                    ),
                )
            conn.commit()
        
        logger.info(f"Saved gap report {report_id} with {len(report.suggestions)} suggestions.")

    async def get_latest_gap_report(self, project_id: str) -> Optional[GapReport]:
        with db_session() as conn:
            # Get latest report header
            row = conn.execute(
                """
                SELECT * FROM gap_reports 
                WHERE project_id = ? 
                ORDER BY generated_at DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()

            if not row:
                return None

            report_id = row["id"]
            generated_at = datetime.fromisoformat(row["generated_at"])

            # Get suggestions
            s_rows = conn.execute(
                "SELECT * FROM gap_suggestions WHERE report_id = ?", (report_id,)
            ).fetchall()

            suggestions = [
                GapSuggestion(
                    id=r["id"],
                    project_id=r["project_id"],
                    ticket_id=r["ticket_id"],
                    status=r["status"],
                    notes=r["notes"],
                    confidence=r["confidence"],
                    related_files=json.loads(r["related_files_json"] or "[]"),
                )
                for r in s_rows
            ]

            return GapReport(
                project_id=project_id,
                generated_at=generated_at,
                suggestions=suggestions,
            )

    async def list_gap_reports(self, project_id: str, limit: int = 20) -> Sequence[GapReport]:
        # Note: This might be heavy if reports are huge. Consider returning a lightweight summary model if needed.
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT * FROM gap_reports 
                WHERE project_id = ? 
                ORDER BY generated_at DESC LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()

        reports = []
        for row in rows:
            # For list view, we usually re-query details or join. 
            # Re-using the logic from get_latest roughly:
            report_id = row["id"]
            with db_session() as conn:
                s_rows = conn.execute(
                    "SELECT * FROM gap_suggestions WHERE report_id = ?", (report_id,)
                ).fetchall()
            
            suggestions = [
                GapSuggestion(
                    id=r["id"],
                    project_id=r["project_id"],
                    ticket_id=r["ticket_id"],
                    status=r["status"],
                    notes=r["notes"],
                    confidence=r["confidence"],
                    related_files=json.loads(r["related_files_json"] or "[]"),
                )
                for r in s_rows
            ]
            
            reports.append(
                GapReport(
                    project_id=row["project_id"],
                    generated_at=datetime.fromisoformat(row["generated_at"]),
                    suggestions=suggestions,
                )
            )

        return reports


# Singleton Accessor

_default_repo = SqliteGapAnalysisRepo()


def get_gap_analysis_repo() -> GapAnalysisRepo:
    return _default_repo

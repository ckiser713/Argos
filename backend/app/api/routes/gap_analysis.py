from __future__ import annotations

from typing import List

from app.domain.gap_analysis import GapReport
from app.repos.gap_analysis_repo import GapAnalysisRepo, get_gap_analysis_repo
from app.services.gap_analysis_service import GapAnalysisService, get_gap_analysis_service
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(tags=["gap-analysis"])


def get_gap_analysis_service_dep() -> GapAnalysisService:
    return get_gap_analysis_service()


def get_gap_analysis_repo_dep() -> GapAnalysisRepo:
    return get_gap_analysis_repo()


@router.post("/projects/{project_id}/gap-analysis/run", response_model=GapReport)
async def run_gap_analysis(
    project_id: str,
    service: GapAnalysisService = Depends(get_gap_analysis_service_dep),
    repo: GapAnalysisRepo = Depends(get_gap_analysis_repo_dep),
) -> GapReport:
    """
    Trigger a new gap analysis run for the given project and persist the report.
    """
    report = await service.generate_gap_report(project_id)
    await repo.save_gap_report(report)
    return report


@router.post("/projects/{project_id}/gap-analysis/generate", response_model=GapReport)
async def generate_gap_analysis(
    project_id: str,
    service: GapAnalysisService = Depends(get_gap_analysis_service_dep),
    repo: GapAnalysisRepo = Depends(get_gap_analysis_repo_dep),
) -> GapReport:
    """
    Compatibility alias for generating a gap analysis report.
    """
    report = await service.generate_gap_report(project_id)
    await repo.save_gap_report(report)
    return report


@router.get("/projects/{project_id}/gap-analysis/latest", response_model=GapReport)
async def get_latest_gap_analysis(
    project_id: str,
    repo: GapAnalysisRepo = Depends(get_gap_analysis_repo_dep),
) -> GapReport:
    """
    Fetch the most recent gap analysis report for the given project.
    """
    report = await repo.get_latest_gap_report(project_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No gap analysis report found for project.",
        )
    return report


@router.get("/projects/{project_id}/gap-analysis/history", response_model=List[GapReport])
async def list_gap_analysis_history(
    project_id: str,
    limit: int = 20,
    repo: GapAnalysisRepo = Depends(get_gap_analysis_repo_dep),
) -> List[GapReport]:
    """
    List historical gap analysis reports for the given project, newest first.
    """
    reports = await repo.list_gap_reports(project_id, limit=limit)
    return list(reports)

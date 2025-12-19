from .agent_service import agent_service
from .context_service import context_service
from .gap_analysis_service import (
    GapAnalysisService,
    configure_gap_analysis_service,
    generate_gap_report,
    get_gap_analysis_service,
)
from .knowledge_service import knowledge_service
from .project_intel_service import (
    cluster_ideas,
    extract_idea_candidates_from_segments,
    promote_clusters_to_tickets,
)
from .system_metrics_service import get_system_status, set_active_agent_runs_stub, set_context_usage_stub
from .workflow_service import workflow_service
from typing import TYPE_CHECKING

__all__ = [
    "get_system_status",
    "set_context_usage_stub",
    "set_active_agent_runs_stub",
    "context_service",
    "workflow_service",
    "get_ingest_service",
    "ingest_service",
    "agent_service",
    "extract_idea_candidates_from_segments",
    "cluster_ideas",
    "promote_clusters_to_tickets",
    "GapAnalysisService",
    "configure_gap_analysis_service",
    "get_gap_analysis_service",
    "generate_gap_report",
    "knowledge_service",
]

if TYPE_CHECKING:
    from .ingest_service import IngestService as IngestService


def get_ingest_service():
    from .ingest_service import ingest_service as service

    return service


class _LazyIngestService:
    def __getattr__(self, item):
        return getattr(get_ingest_service(), item)

    def __call__(self, *args, **kwargs):
        return get_ingest_service()(*args, **kwargs)


ingest_service = _LazyIngestService()

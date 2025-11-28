from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Protocol, Sequence, Tuple, runtime_checkable

from pydantic import BaseModel

from app.domain.gap_analysis import GapReport, GapStatus, GapSuggestion

# --- Imports for Real Implementations ---
from app.repos import project_intel_repo
from app.services import llm_service

logger = logging.getLogger(__name__)


@runtime_checkable
class IdeaTicket(Protocol):
    """
    Structural protocol for the IdeaTicket objects exposed by the Project Intelligence layer.
    Only the attributes required for gap analysis are specified here.
    """

    id: str
    project_id: str
    title: str
    description: str


class CodeChunk(BaseModel):
    """
    Lightweight view of a code chunk returned from vector search.
    """

    file_path: str
    content: str
    similarity: float


class IdeaTicketProvider(Protocol):
    async def list_tickets_for_project(self, project_id: str) -> Sequence[IdeaTicket]:
        """
        Return all IdeaTickets for a given project.
        """


class CodeSearchBackend(Protocol):
    async def search_related_code(self, ticket: IdeaTicket, *, top_k: int) -> Sequence[CodeChunk]:
        """
        Return code chunks ordered by descending similarity for the given ticket.
        """


class CoderLLMClient(Protocol):
    async def generate_gap_notes(
        self,
        ticket: IdeaTicket,
        code_chunks: Sequence[CodeChunk],
        status: GapStatus,
    ) -> str:
        """
        Produce human-readable notes describing the mapping between the ticket and the code.
        """


@dataclass
class GapAnalysisConfig:
    top_k: int = 8
    implemented_threshold: float = 0.8
    partial_threshold: float = 0.4
    min_high_matches: int = 2


@dataclass
class GapAnalysisService:
    """
    Core gap-analysis orchestration logic.

    This service is intentionally decoupled from concrete storage, vector DBs,
    and LLM runtimes. Those concerns are modeled via small protocol interfaces
    that can be implemented by adapters (e.g., Qdrant-backed search, HTTP LLM client).
    """

    ticket_provider: IdeaTicketProvider
    code_search: CodeSearchBackend
    coder_client: CoderLLMClient
    config: GapAnalysisConfig = field(default_factory=GapAnalysisConfig)

    async def generate_gap_report(self, project_id: str) -> GapReport:
        logger.info("Starting gap analysis for project %s", project_id)
        tickets = await self.ticket_provider.list_tickets_for_project(project_id)
        logger.info("Found %d tickets for project %s", len(tickets), project_id)

        suggestions: List[GapSuggestion] = []

        for ticket in tickets:
            # Handle both sync and async code search
            if hasattr(self.code_search, 'search_related_code'):
                if callable(getattr(self.code_search.search_related_code, '__call__', None)):
                    # Check if it's async
                    import inspect
                    if inspect.iscoroutinefunction(self.code_search.search_related_code):
                        code_chunks = await self.code_search.search_related_code(ticket, top_k=self.config.top_k)
                    else:
                        code_chunks = self.code_search.search_related_code(ticket, top_k=self.config.top_k)
                else:
                    code_chunks = []
            else:
                code_chunks = []
                
            status, confidence = self._classify_status(code_chunks)
            logger.debug(
                "Ticket %s classified as %s (confidence=%.3f, matches=%d)",
                ticket.id,
                status,
                confidence,
                len(code_chunks),
            )

            notes = await self.coder_client.generate_gap_notes(
                ticket,
                code_chunks,
                status,
            )

            related_files = sorted({chunk.file_path for chunk in code_chunks})

            suggestion = GapSuggestion(
                id=f"{project_id}:{ticket.id}",
                project_id=project_id,
                ticket_id=ticket.id,
                status=status,
                related_files=related_files,
                notes=notes,
                confidence=confidence,
            )
            suggestions.append(suggestion)

        report = GapReport(
            project_id=project_id,
            generated_at=datetime.now(timezone.utc),
            suggestions=suggestions,
        )
        logger.info(
            "Completed gap analysis for project %s with %d suggestions",
            project_id,
            len(suggestions),
        )
        return report

    def _classify_status(self, code_chunks: Sequence[CodeChunk]) -> Tuple[GapStatus, float]:
        if not code_chunks:
            return "unmapped", 0.0

        implemented_matches = [c for c in code_chunks if c.similarity >= self.config.implemented_threshold]
        partial_matches = [
            c for c in code_chunks if self.config.partial_threshold <= c.similarity < self.config.implemented_threshold
        ]

        if len(implemented_matches) >= self.config.min_high_matches:
            # Confidence is the mean similarity of high matches, capped at 1.0.
            mean_sim = sum(c.similarity for c in implemented_matches) / len(implemented_matches)
            confidence = max(0.0, min(1.0, mean_sim))
            return "implemented", confidence

        if implemented_matches or partial_matches:
            combined = implemented_matches + partial_matches
            # Confidence is driven by the strongest match in the partial range.
            top_sim = max(c.similarity for c in combined)
            normalized = (top_sim - self.config.partial_threshold) / max(
                1e-9, self.config.implemented_threshold - self.config.partial_threshold
            )
            confidence = max(0.0, min(1.0, normalized))
            return "partially_implemented", confidence

        # Low-similarity matches exist but below partial threshold; treat as unmapped with low confidence.
        best_match = max(code_chunks, key=lambda c: c.similarity)
        confidence = max(0.0, min(0.3, best_match.similarity))
        return "unmapped", confidence


# --- Concrete Adapters ---


class ProjectIntelTicketProvider(IdeaTicketProvider):
    async def list_tickets_for_project(self, project_id: str) -> Sequence[IdeaTicket]:
        # Connects to the existing project_intel_repo
        # Make it async-compatible
        from app.services.idea_service import idea_service
        result = idea_service.list_tickets(project_id, limit=1000)
        return result.items if hasattr(result, 'items') else []


class LLMCoderClient(CoderLLMClient):
    async def generate_gap_notes(
        self,
        ticket: IdeaTicket,
        code_chunks: Sequence[CodeChunk],
        status: GapStatus,
    ) -> str:
        # Connects to the existing llm_service
        context_str = "\n\n".join(
            [f"File: {c.file_path}\nContent:\n{c.content}" for c in code_chunks]
        )
        prompt = (
            f"Analyze the gap for the following ticket:\n"
            f"Title: {ticket.title}\n"
            f"Description: {ticket.description}\n\n"
            f"Status classified as: {status}\n\n"
            f"Relevant Code Context:\n{context_str}\n\n"
            f"Task: Provide a concise set of notes explaining the implementation gap or existing logic. "
            f"If implemented, explain how. If missing, explain what needs to be added."
        )

        return llm_service.generate_text(
            prompt=prompt,
            project_id=ticket.project_id,
            temperature=0.0,
            max_tokens=1000,
        )


class NullTicketProvider(IdeaTicketProvider):
    async def list_tickets_for_project(self, project_id: str) -> Sequence[IdeaTicket]:
        logger.warning("NullTicketProvider in use; returning no tickets for project %s", project_id)
        return []


class NullCodeSearchBackend(CodeSearchBackend):
    async def search_related_code(self, ticket: IdeaTicket, *, top_k: int) -> Sequence[CodeChunk]:
        logger.warning("NullCodeSearchBackend in use; returning no code matches for ticket %s", ticket.id)
        return []


class NullCoderLLMClient(CoderLLMClient):
    async def generate_gap_notes(
        self,
        ticket: IdeaTicket,
        code_chunks: Sequence[CodeChunk],
        status: GapStatus,
    ) -> str:
        if status == "unmapped":
            return f"No related code was found for ticket '{ticket.title}' ({ticket.id})."
        if status == "implemented":
            files = sorted({c.file_path for c in code_chunks})
            return "Ticket appears to be implemented. Related files: " + ", ".join(files)
        if status == "partially_implemented":
            files = sorted({c.file_path for c in code_chunks})
            return "Ticket appears to be partially implemented across: " + ", ".join(files)
        return "Gap analysis status is unknown; no additional details are available."


_default_service: Optional[GapAnalysisService] = None


def configure_gap_analysis_service(service: GapAnalysisService) -> None:
    """
    Configure the module-level service used by the convenience generate_gap_report() function.
    """
    global _default_service
    _default_service = service
    logger.info("GapAnalysisService configured: %r", service)


def get_gap_analysis_service() -> GapAnalysisService:
    if _default_service is None:
        # Import inside function to avoid circular imports with qdrant_code_search
        try:
            from app.services.qdrant_code_search import QdrantCodeSearchBackend

            configure_gap_analysis_service(
                GapAnalysisService(
                    ticket_provider=ProjectIntelTicketProvider(),
                    code_search=QdrantCodeSearchBackend(),
                    coder_client=LLMCoderClient(),
                )
            )
        except Exception as e:
            logger.error(f"Failed to initialize real GapAnalysisService: {e}. Falling back to Null services.")
            configure_gap_analysis_service(
                GapAnalysisService(
                    ticket_provider=NullTicketProvider(),
                    code_search=NullCodeSearchBackend(),
                    coder_client=NullCoderLLMClient(),
                )
            )

    assert _default_service is not None
    return _default_service


async def generate_gap_report(project_id: str) -> GapReport:
    """
    Convenience wrapper matching the requested signature.
    """
    service = get_gap_analysis_service()
    return await service.generate_gap_report(project_id)

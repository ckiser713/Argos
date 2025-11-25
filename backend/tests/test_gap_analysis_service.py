import pytest

from app.domain.gap_analysis import GapStatus
from app.services.gap_analysis_service import (
    CodeChunk,
    GapAnalysisConfig,
    GapAnalysisService,
    IdeaTicket,
    IdeaTicketProvider,
    CodeSearchBackend,
    CoderLLMClient,
)


class FakeTicket:
    def __init__(self, id: str, project_id: str, title: str, description: str) -> None:
        self.id = id
        self.project_id = project_id
        self.title = title
        self.description = description


class FakeTicketProvider(IdeaTicketProvider):
    def __init__(self, tickets):
        self._tickets = tickets

    async def list_tickets_for_project(self, project_id: str):
        return [t for t in self._tickets if t.project_id == project_id]


class FakeCodeSearchBackend(CodeSearchBackend):
    def __init__(self, matches_by_ticket_id):
        self._matches_by_ticket_id = matches_by_ticket_id

    async def search_related_code(self, ticket: IdeaTicket, *, top_k: int):
        matches = self._matches_by_ticket_id.get(ticket.id, [])
        return matches[:top_k]


class FakeCoderLLMClient(CoderLLMClient):
    async def generate_gap_notes(self, ticket, code_chunks, status: GapStatus) -> str:
        return f"{status} for {ticket.id} with {len(code_chunks)} matches"


@pytest.mark.asyncio
async def test_generate_gap_report_unmapped():
    ticket = FakeTicket(id="T1", project_id="P1", title="A feature", description="Do something")
    ticket_provider = FakeTicketProvider([ticket])
    search_backend = FakeCodeSearchBackend(matches_by_ticket_id={})
    coder_client = FakeCoderLLMClient()

    service = GapAnalysisService(
        ticket_provider=ticket_provider,
        code_search=search_backend,
        coder_client=coder_client,
        config=GapAnalysisConfig(implemented_threshold=0.8, partial_threshold=0.4),
    )

    report = await service.generate_gap_report("P1")
    assert report.project_id == "P1"
    assert len(report.suggestions) == 1
    suggestion = report.suggestions[0]
    assert suggestion.ticket_id == "T1"
    assert suggestion.status == "unmapped"
    assert suggestion.confidence == 0.0
    assert suggestion.related_files == []
    assert suggestion.notes == "unmapped for T1 with 0 matches"


@pytest.mark.asyncio
async def test_generate_gap_report_implemented():
    ticket = FakeTicket(id="T2", project_id="P1", title="Implemented feature", description="Do X")
    ticket_provider = FakeTicketProvider([ticket])

    matches = [
        CodeChunk(file_path="a.py", content="code a", similarity=0.9),
        CodeChunk(file_path="b.py", content="code b", similarity=0.92),
        CodeChunk(file_path="c.py", content="code c", similarity=0.5), # This one should not be considered "implemented" by default config if min_high_matches is 2
    ]
    search_backend = FakeCodeSearchBackend(matches_by_ticket_id={"T2": matches})
    coder_client = FakeCoderLLMClient()

    service = GapAnalysisService(
        ticket_provider=ticket_provider,
        code_search=search_backend,
        coder_client=coder_client,
        config=GapAnalysisConfig(
            top_k=5,
            implemented_threshold=0.8,
            partial_threshold=0.4,
            min_high_matches=2,
        ),
    )

    report = await service.generate_gap_report("P1")
    suggestion = report.suggestions[0]
    assert suggestion.status == "implemented"
    # Both a.py and b.py should be surfaced in related_files.
    assert "a.py" in suggestion.related_files
    assert "b.py" in suggestion.related_files
    # Note that c.py will also be included in related_files because the service gathers all.
    assert "c.py" in suggestion.related_files
    assert 0.8 <= suggestion.confidence <= 1.0 # The mean of implemented_matches (0.9, 0.92)
    assert suggestion.notes == "implemented for T2 with 3 matches" # CoderLLMClient receives all chunks


@pytest.mark.asyncio
async def test_generate_gap_report_partially_implemented():
    ticket = FakeTicket(id="T3", project_id="P1", title="Partial feature", description="Do Y")
    ticket_provider = FakeTicketProvider([ticket])

    matches = [
        CodeChunk(file_path="partial.py", content="code", similarity=0.6),
        CodeChunk(file_path="low.py", content="code", similarity=0.3),
    ]
    search_backend = FakeCodeSearchBackend(matches_by_ticket_id={"T3": matches})
    coder_client = FakeCoderLLMClient()

    service = GapAnalysisService(
        ticket_provider=ticket_provider,
        code_search=search_backend,
        coder_client=coder_client,
        config=GapAnalysisConfig(
            top_k=5,
            implemented_threshold=0.8,
            partial_threshold=0.4,
            min_high_matches=2,
        ),
    )

    report = await service.generate_gap_report("P1")
    suggestion = report.suggestions[0]
    assert suggestion.status == "partially_implemented"
    assert "partial.py" in suggestion.related_files
    assert "low.py" in suggestion.related_files
    assert 0.0 < suggestion.confidence <= 1.0 # Based on (top_sim - partial_threshold) / (implemented_threshold - partial_threshold)
    assert suggestion.notes == "partially_implemented for T3 with 2 matches"

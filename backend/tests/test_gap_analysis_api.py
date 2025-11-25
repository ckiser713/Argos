import pytest
from app.api.routes.gap_analysis import (
    get_gap_analysis_repo_dep,
    get_gap_analysis_service_dep,
)
from app.api.routes.gap_analysis import (
    router as gap_router,
)
from app.domain.gap_analysis import GapReport
from app.repos.gap_analysis_repo import GapAnalysisRepo
from app.services.gap_analysis_service import (
    CodeChunk,
    CoderLLMClient,
    CodeSearchBackend,
    GapAnalysisConfig,
    GapAnalysisService,
    IdeaTicket,
    IdeaTicketProvider,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


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
    async def generate_gap_notes(self, ticket, code_chunks, status):
        return f"{status} for {ticket.id} with {len(code_chunks)} matches"


class InMemoryTestGapRepo(GapAnalysisRepo):
    def __init__(self) -> None:
        self._reports = {}

    async def save_gap_report(self, report: GapReport) -> None:
        self._reports.setdefault(report.project_id, [])
        self._reports[report.project_id].append(report)
        self._reports[report.project_id].sort(key=lambda r: r.generated_at, reverse=True)

    async def get_latest_gap_report(self, project_id: str):
        reports = self._reports.get(project_id) or []
        return reports[0] if reports else None

    async def list_gap_reports(self, project_id: str, limit: int = 20):
        reports = self._reports.get(project_id) or []
        return reports[:limit]


@pytest.fixture
def app_with_gap_api():
    app = FastAPI()
    app.include_router(gap_router)

    # Configure fake dependencies.
    tickets = [
        FakeTicket(id="T1", project_id="P1", title="Feature A", description="Do A"),
        FakeTicket(id="T2", project_id="P1", title="Feature B", description="Do B"),
    ]
    matches_by_ticket_id = {
        "T1": [
            CodeChunk(file_path="a.py", content="code", similarity=0.9),
            CodeChunk(file_path="b.py", content="code", similarity=0.85),
        ],
        "T2": [],
    }
    ticket_provider = FakeTicketProvider(tickets)
    search_backend = FakeCodeSearchBackend(matches_by_ticket_id=matches_by_ticket_id)
    coder_client = FakeCoderLLMClient()

    service = GapAnalysisService(
        ticket_provider=ticket_provider,
        code_search=search_backend,
        coder_client=coder_client,
        config=GapAnalysisConfig(),
    )
    repo = InMemoryTestGapRepo()

    app.dependency_overrides[get_gap_analysis_service_dep] = lambda: service
    app.dependency_overrides[get_gap_analysis_repo_dep] = lambda: repo

    return app


@pytest.fixture
def client(app_with_gap_api):
    return TestClient(app_with_gap_api)


def test_run_gap_analysis_and_get_latest(client: TestClient):
    response = client.post("/projects/P1/gap-analysis/run")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == "P1"
    assert len(data["suggestions"]) == 2

    # Latest should return the same report.
    latest_response = client.get("/projects/P1/gap-analysis/latest")
    assert latest_response.status_code == 200
    latest_data = latest_response.json()
    assert latest_data["project_id"] == "P1"
    assert len(latest_data["suggestions"]) == 2


def test_gap_analysis_history(client: TestClient):
    # Run twice to create history.
    r1 = client.post("/projects/P1/gap-analysis/run")
    assert r1.status_code == 200
    r2 = client.post("/projects/P1/gap-analysis/run")
    assert r2.status_code == 200

    history_response = client.get("/projects/P1/gap-analysis/history?limit=10")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 2

    # Ensure the reports are ordered newest-first by generated_at.
    first_generated = history[0]["generated_at"]
    second_generated = history[1]["generated_at"]
    assert first_generated >= second_generated


def test_latest_gap_analysis_not_found(client: TestClient):
    # Different project with no reports.
    response = client.get("/projects/UNKNOWN/gap-analysis/latest")
    assert response.status_code == 404

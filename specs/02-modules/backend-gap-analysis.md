## Overview
- Gap analysis orchestration that classifies tickets against code search results and generates reports with suggestions, using pluggable providers for tickets, code search, and LLM notes (`backend/app/services/gap_analysis_service.py:69-238`).
- SQLite repository to persist and retrieve gap reports/suggestions, plus FastAPI routes to run and fetch reports (`backend/app/repos/gap_analysis_repo.py:23-167`, `backend/app/api/routes/gap_analysis.py:21-62`).

## Responsibilities & Non-Responsibilities
- Responsibilities: fetch tickets via provider, search related code, classify status (implemented/partial/unmapped), generate notes via coder client, assemble/summarize suggestions, persist/retrieve reports.
- Non-Responsibilities: scheduling/automation of gap runs, UI formatting, security/access control, vector search/LLM implementation details (delegated to adapters), migrations.

## Dependencies & Integration Points
- Protocol adapters: `IdeaTicketProvider`, `CodeSearchBackend`, `CoderLLMClient` (protocols in `gap_analysis_service.py:19-66`).
- Default adapters: `ProjectIntelTicketProvider` pulls from `project_intel_repo`; `LLMCoderClient` uses `llm_service.generate_text`; null adapters provided for degenerate cases (`backend/app/services/gap_analysis_service.py:174-237`).
- Domain models: `GapReport`, `GapSuggestion`, `GapStatus` (`backend/app/domain/gap_analysis.py`), `IdeaTicket` (protocol).
- Repo uses SQLite tables `gap_reports`, `gap_suggestions` (`backend/app/db.py:327-347`) and `db_session`.
- API endpoints under `/api/projects/{project_id}/gap-analysis/*` (`backend/app/api/routes/gap_analysis.py`).

## Interfaces & Contracts
**Service** (`backend/app/services/gap_analysis_service.py`):
- `GapAnalysisService.generate_gap_report(project_id) -> GapReport` async: iterates tickets, searches code, classifies status via `_classify_status`, generates notes via coder client, builds `GapSuggestion` list, returns `GapReport` with timestamp.
- Classification thresholds configurable via `GapAnalysisConfig` (top_k, implemented_threshold, partial_threshold, min_high_matches).
- `_classify_status(code_chunks)` returns (status, confidence) based on similarity thresholds.

**Repo** (`backend/app/repos/gap_analysis_repo.py`):
- `save_gap_report(report)` async: inserts row into `gap_reports` with generated UUID; inserts suggestions into `gap_suggestions`; report model lacks id so DB uses internal id.
- `get_latest_gap_report(project_id)` async: fetches latest report and suggestions; returns GapReport or None.
- `list_gap_reports(project_id, limit)` async: returns sequence of reports with suggestions.

**API** (`backend/app/api/routes/gap_analysis.py`):
- `POST /api/projects/{project_id}/gap-analysis/run` → runs analysis, persists report, returns GapReport (`21-32`).
- `GET /api/projects/{project_id}/gap-analysis/latest` → latest report or 404 (`35-49`).
- `GET /api/projects/{project_id}/gap-analysis/history?limit=` → list recent reports (`52-62`).

## Data Models
- `GapReport {project_id, generated_at, suggestions[]}`; DB also stores id not present in model.
- `GapSuggestion {id, project_id, ticket_id, status implemented|partially_implemented|unmapped, notes, confidence, related_files[]}`.
- `GapStatus` values tied to classification thresholds.

## Control Flows
- Run: service fetches tickets → code search `top_k` → classify → generate notes → build suggestions → return report → repo saves report/suggestions.
- Classification: counts high similarity matches ≥ implemented_threshold; partial range between partial/implemented thresholds; confidence derived from mean/top similarity.
- Persistence: repo writes report then suggestions in one transaction; retrieval reconstructs report with suggestions.

## Config & Runtime Parameters
- `GapAnalysisConfig`: `top_k=8`, thresholds (0.8 implemented, 0.4 partial), min_high_matches=2; not exposed via API.
- LLM model/temperature passed via `llm_service.generate_text` (hardcoded model "gpt-4o", temp 0.0) in default coder client.

## Error & Failure Semantics
- Service relies on async providers; exceptions propagate unless caught by providers/llm_service.
- Repo uses async signatures but synchronous sqlite; no transaction rollback on partial failure beyond commit boundary.
- API returns 404 when no report found; other errors bubble as 500.
- Model/report id mismatch: `GapReport` lacks id; related suggestions use ticket_id for id.

## Observability
- Logging around start/end/classification; warnings in null providers; no metrics.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Async service uses sync sqlite repo; may block event loop. [ASSUMPTION] load is low.
- Thresholds/config not tunable per project; notes generation uses hardcoded model.
- No auth/ownership checks; endpoints rely on global deps.
- No deduplication or paging for suggestions; large ticket sets may be heavy.
- Null adapters may silently return empty results; need explicit configuration for production.

## Verification Ideas
- Service unit tests with stub providers: verify status classification and confidence with crafted similarity sets; ensure related_files extracted.
- Repo tests: save/report retrieval round-trip, latest ordering, history limit.
- API tests: run analysis returns GapReport; latest/history endpoints behavior when empty vs populated; error handling for missing reports.

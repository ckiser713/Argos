## Current Test Landscape
- Backend pytest suite: `backend/tests/` covers projects, context, ingest, knowledge, gap analysis, workflows, agents, mode, system metrics; some tests have mismatches with current APIs (e.g., agent/ingest payloads).
- Frontend unit tests: components and hooks under `frontend/src/components/__tests__` and `frontend/src/hooks/__tests__`.
- E2E Playwright suite: specs under `e2e/` (ingest, knowledge, projects, roadmap, agents, websocket, UI components, performance, accessibility). TODOs remain for WebSocket client coverage and UI states.
- Legacy/aux specs in `docs/specs/` outlining missing tests and features; many TBDs noted.

## Gaps & Risks
- No automated migrations or DB schema validation.
- Workflow execution logic stubbed; tests can pass while functionality absent.
- Agent profile/contract mismatches cause failing/ineffective tests.
- Streaming/WebSocket coverage incomplete; real-time behavior unverified.
- No load/performance guardrails; no chaos/failure injection.
- Auth bypass in /api/token and streaming routes not tested/hardened.
- Frontend hooks may drift from backend API contracts; limited contract tests.

## Proposed Quality Gates
- **API Contract Tests**: For each route, assert status codes, required fields, and error cases (404/400/409). Include project scoping checks.
- **Schema Alignment**: Tests to ensure DB schema matches domain models and API responses (detect NULL into non-optional fields).
- **Workflow/Agent Execution**: Integration tests for run lifecycle, node state updates, events emitted, and cancellation/pause/resume semantics.
- **Ingest**: Tests for create/cancel/delete, file-not-found handling, RAG ingestion calls (mocked), and message vs error_message correctness.
- **Knowledge/Qdrant**: Tests for node/edge CRUD, duplicate/validation errors, vector search fallback behavior.
- **Ideas/Roadmap**: CRUD tests with dependency/cycle validation and mission-control mapping; ensure delete protections.
- **Streaming**: WebSocket/SSE tests for ingest/agent/workflow events, auth enforcement, reconnect/backpressure scenarios.
- **Auth**: Token issuance/verification tests; enforce auth on protected routes; negative cases.
- **Frontend**: Hook tests with mocked fetch to validate request/response mapping; component tests for ErrorBoundary/Toast; E2E flows aligned to backend contracts; expand WebSocket client tests.
- **Performance/Resilience**: Add timeouts/retries in services and test them; basic load tests for ingest/agent/workflow concurrency; simulate Qdrant/LLM outages.

## Process Suggestions
- Require tests for new endpoints/features and updates to specs (`specs/README.md` structure).
- Add CI steps: lint (ruff/mypy/ts), backend tests, frontend tests, e2e smoke (select critical flows), schema drift check.
- Track gaps via `specs/99-gaps-and-risks.md`; close items with corresponding tests and spec updates.

---
name: multi-orchestrator-e2e-deployable
overview: Plan-only phases for making E2E stack deployable locally via docker/compose and Playwright.
todos: []
---

# Multi-Persona Orchestrator Plan – E2E Deployable (Plan-Only)

## Phase 1 - Scope & Scan

- Goal summary: ensure Playwright E2E suite runs reliably end-to-end for local deployability; align docker-compose stack (backend/frontend/worker/qdrant/redis/minio/playwright) with test env; make scripts deterministic for local runs.
- Likely subsystems: Playwright config & fixtures; docker-compose.e2e stack + Dockerfiles; local runner scripts (`run_e2e.sh`, `run_e2e_nix.sh`, `tools/run_e2e_local.sh`, `tools/entrypoint_playwright.sh`); backend env (CORTEX_*), celery worker, storage (MinIO), vector DB (Qdrant); frontend build/serve pipeline.
- Files to inspect: `docker-compose.e2e.yml` (service wiring/env), `Dockerfile.backend` (runtime deps), `Dockerfile.frontend` (build/serve), `Dockerfile.playwright` + `tools/entrypoint_playwright.sh` (test runner), `tools/run_e2e_local.sh` (local orchestration), `playwright.config.ts` & `e2e/fixtures.ts` (base URLs, auth skips), `e2e/utils/api-helpers.ts` (API coverage), `run_e2e.sh` / `run_e2e_nix.sh` (top-level entry), docs `E2E_TESTING_SETUP.md` (expected flow).
- **Phase 1: No edits performed.**

## Phase 2 - Specialist Reviews

- [FE]
- What works: frontend Dockerfile builds static assets and serves via `serve` on 5173; Playwright config respects `PLAYWRIGHT_BASE_URL`, includes viewport and multi-browser projects; fixtures set deterministic viewport/styles.
- Broken/risky: preview/build base URLs may diverge from compose values; no explicit wait-for-frontend in entrypoint; Vite env not enforced for preview/run scripts, risking API mismatch when deployable stack used.
- MUST-FIX: propagate consistent API/WS base URLs from compose/build args to Playwright and preview server; ensure frontend readiness wait before tests.
- SHOULD-FIX: reduce duplicate base URL definitions and add minimal UI smoke (health/page load) to catch 404/asset issues.
- [BE]
- What works: backend container uses poetry deps and uvicorn; compose sets `CORTEX_SKIP_AUTH`, S3 via MinIO, Redis/Celery worker defined; test DB path isolated (`test_atlas.db`).
- Broken/risky: no migration/seed step before tests; MinIO bucket not auto-created; qdrant not health-gated; mock lanes only set in local script (not compose) so backend may expect real models; worker depends_on qdrant but backend does not.
- MUST-FIX: add startup wait/health checks and bucket creation; ensure `CORTEX_E2E_MOCK_LANES` (or equivalent) set in compose to avoid model deps; run migrations/init before tests.
- SHOULD-FIX: align backend/worker env with PLAYWRIGHT_API_BASE and storage URLs; add graceful shutdown for spawned uvicorn in local runner.
- [INFRA]
- What works: dedicated `docker-compose.e2e.yml` with backend/frontend/worker/qdrant/redis/minio/playwright; Dockerfile.playwright installs deps/browsers; local scripts attempt port cleanup and qdrant bring-up.
- Broken/risky: compose lacks health checks/depends_on for qdrant/minio readiness; mixed entrypoints (Nix vs compose) can diverge; no seeded bucket volume; playwright entrypoint re-installs each run and lacks wait-for services; backend test DB not volume-mounted (ephemeral) – ok but migrations need ensuring.
- MUST-FIX: choose canonical runner (compose) and add health/ready gating; ensure MinIO bucket bootstrap and qdrant health; make Playwright container wait on backend/frontend URLs before testing.
- SHOULD-FIX: dedupe install steps (cache pnpm/browsers) and document env toggles; align port mappings with local host for debugging.
- [QA]
- Current: Playwright config has retries on CI, traces/screenshots on failure; fixtures create/delete projects; wide API coverage in helpers.
- Gaps: no smoke test for `/system/health`/`/system/ready`; no check that MinIO bucket exists; no guard that backend is using mock lanes (otherwise model fetch may hang); report publishing flow not described for local compose.
- Tests to add: health/readiness smoke; storage bucket existence; mock-lane flag assertion; optional minimal UI page-load smoke hitting frontend with real assets.
- **Phase 2: Analysis only, no edits performed.**

## Phase 3 - Round Table & Decisions

- Round table: FE wants consistent base URLs and frontend readiness waits; BE insists on migrations, mock lanes, bucket creation; INFRA prioritizes compose as canonical runner with health gating; QA needs smoke coverage for health/storage/mock toggles. Agreed to standardize on compose-first runner with explicit waits and env propagation; add minimal smoke tests; keep Nix/local runner aligned to compose env.
- DECISION SUMMARY:
- [INFRA][BE] Make `docker-compose.e2e.yml` the canonical e2e stack with health checks/depends_on and env parity (mock lanes, storage, redis/qdrant/minio waits).
- [BE] Add migrations/init + MinIO bucket bootstrap before tests (compose or runner script).
- [INFRA] Update Playwright entrypoint to wait on backend/frontend URLs and honor `PLAYWRIGHT_BASE_URL`/`PLAYWRIGHT_API_BASE` from compose.
- [FE][INFRA] Propagate API/WS base URLs consistently through Vite build/preview and compose build args; avoid drift between preview and compose runtime.
- [QA] Add smoke tests for system health/ready, bucket presence, and mock-lane flag to fail fast.
- [INFRA][QA] Document one-liner to run e2e locally (compose) and how to view reports.
- **Phase 3: Decisions only, no edits performed.**

## Phase 4 - EDIT PLAN (Ordered, No Edits Yet)

1) File: `docker-compose.e2e.yml`

- [INFRA][BE] Add healthchecks for backend, frontend, qdrant, minio; wire `depends_on` with `condition: service_healthy`; propagate `CORTEX_E2E_MOCK_LANES=1` (or similar) to backend/worker; ensure storage/env parity and optional init command for migrations; consider shared volume for test DB if persistence needed.
- [QA] Validate compose up with `--abort-on-container-exit` runs clean and services report healthy before tests.

2) File: `tools/entrypoint_playwright.sh` (and, if needed, `Dockerfile.playwright`)

- [INFRA] Add wait/poll loop against `$PLAYWRIGHT_BASE_URL` and `$PLAYWRIGHT_API_BASE/system/ready` before running tests; avoid reinstalling browsers when already baked in image; allow `PLAYWRIGHT_TEST_ARGS` passthrough.
- [QA] Ensure non-zero exit on failed wait; keep report artifacts location stable.

3) File: `tools/run_e2e_local.sh`

- [INFRA][BE] Align local runner env with compose (mock lanes, storage URLs); run migrations/init for `test_atlas.db`; bootstrap MinIO bucket (via `mc`/`aws s3api`); add qdrant/minio readiness checks; keep port cleanup.
- [QA] Re-run local smoke (health + sample API call) before Playwright; bubble exit code.

4) File: `playwright.config.ts`

- [FE][INFRA] Ensure baseURL/API base defaults align with compose; optionally gate `webServer` to start local dev server only when not using compose; adjust timeouts if service warmup increases; centralize reporter output.
- [QA] Keep retries/timeouts tuned; verify traces/screenshots path matches CI expectations.

5) File: `e2e/fixtures.ts`

- [BE][QA] Use shared `API_BASE` that respects compose env; add preflight call to `/system/health`/`/system/ready` in fixtures; ensure cleanup resilience even on failures.
- [QA] Add assertion that mock lanes flag is active (if applicable) to avoid real model pulls.

6) File: `e2e/health.spec.ts` (new)

- [QA] Add smoke covering frontend page load, backend `/system/health`/`ready`, MinIO bucket existence (via API helper) and qdrant reachability; fast-fail before heavier suites.

7) File: `E2E_TESTING_SETUP.md` (and, if necessary, `.github/workflows/e2e.yml` reference)
# Spec Suite Map

This directory houses living specifications derived from the checked-in code. Each spec must cite evidence (file paths and line ranges) and flag any inference with `[ASSUMPTION]`. Update the specs whenever behavior changes so they remain the source of truth for refactors and onboarding.

## Files and Roles
- `00-system-overview.md` — Goals, scope, primary user/data flows, external dependencies.
- `01-architecture-topology.md` — Components, boundaries, deployment/runtime topology, failure domains.
- `02-modules/` — One spec per significant module or service; see planned files below.
- `03-data-contracts.md` — Cross-cutting entities, schemas, relationships, and migration/versioning notes.
- `04-runtime-and-ops.md` — How to run the system (envs, processes, jobs), operational knobs, and SLO-style expectations.
- `05-quality-gates-and-testing.md` — Current test strategy, gaps, and enforceable quality gates tied to risks.
- `99-gaps-and-risks.md` — Unmapped files, unknown behaviors, fragile flows, and follow-up actions with severity tags.

## Planned Module Specs (`02-modules/`)
Backend services (FastAPI app under `backend/app`):
- `backend-core.md` — App creation, routing, config, DB initialization, auth middleware, settings.
- `backend-auth.md` — `auth_service`, token verification, `/api/auth` routes.
- `backend-system-and-metrics.md` — `system_service`, `system_metrics_service`, `/api/system`.
- `backend-projects-and-mode.md` — `project_service`, `mode_repo`, `/api/projects` and `/api/mode`.
- `backend-context.md` — `context_service`, context domain models, `/api/context`.
- `backend-ingest.md` — `ingest_service`, ingest sources/jobs, `/api/ingest`.
- `backend-knowledge-and-qdrant.md` — `knowledge_service`, `qdrant_service`, `qdrant_code_search`, `/api/knowledge`.
- `backend-ideas-and-intel.md` — `idea_service`, `project_intel_service`, idea tickets/clusters, `/api/ideas`, `/api/project-intel`.
- `backend-agents-and-streaming.md` — `agent_service`, streaming endpoints, agent runs/messages/steps, `/api/agents`, `/api/stream`.
- `backend-workflows-and-graphs.md` — `workflow_service`, `workflow_compiler`, `graphs/`, `/api/workflows`.
- `backend-gap-analysis.md` — `gap_analysis_service`, `gap_analysis_repo`, `/api/gap-analysis`.
- `backend-roadmap.md` — `roadmap_service`, roadmap nodes/edges, `/api/roadmap`.
- `backend-llm-and-rag.md` — `llm_service`, `llama_cpp_service`, `rag_service`, LLM backend selection and prompt/embedding flows.
- `backend-domain-models.md` — Domain models in `app/domain/`, shared enums/types, serialization rules.

Frontend app (React + Vite under `frontend/src`):
- `frontend-app-shell.md` — `App.tsx`, entrypoints, providers, routing/layout concerns.
- `frontend-domain-and-store.md` — `domain/`, `state/`, API client in `lib/`, shared types and data shaping.
- `frontend-hooks-and-components.md` — Hooks in `hooks/`, UI components, error/toast handling, test utilities.

Testing and auxiliary components:
- `e2e-suite.md` — Playwright specs under `e2e/` and UI subfolder, fixtures/utils.
- `frontend-unit-tests.md` — Component/hook tests under `frontend/src/components/__tests__` and `frontend/src/hooks/__tests__`.
- `mcp-noauth-server.md` — TypeScript MCP server under `mcp-noauth-server/`.

## How to Extend and Keep in Sync
- When behavior changes, update the relevant module spec and any affected system/data/ops files in the same change.
- Cross-link specs via file paths (e.g., `backend/app/services/context_service.py:42`) and tag uncertainties with `[ASSUMPTION]` plus a verification note.
- If you touch files not covered by an existing module spec, add a new `02-modules/*.md` entry and reference it from `99-gaps-and-risks.md` until filled.
- Keep `03-data-contracts.md` aligned with schema changes in `app/db.py` and domain models; reflect env/config shifts in `04-runtime-and-ops.md`.
- Use `05-quality-gates-and-testing.md` to capture new tests and guardrails; log any missing coverage in `99-gaps-and-risks.md`.
- Run all project commands inside the Nix dev shell (`nix develop` or `nix-shell nix/rocm-shell.nix`). Use `tools/require-nix.sh <command>` in scripts/CI to enforce the guardrail; avoid creating ad-hoc virtualenvs outside Nix.

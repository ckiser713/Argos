## Overview
- FastAPI application bootstrap that wires config, DB initialization, auth dependency selection, CORS, and router registration (`backend/app/main.py:25-67`).
- Centralized settings model with env-var overrides for auth, LLM, Qdrant, execution modes, and DB paths (`backend/app/config.py:9-59`).
- SQLite connection/session helpers and upfront schema creation via `init_db()` (`backend/app/db.py:11-350`).

## Responsibilities & Non-Responsibilities
- Responsibilities: load settings once, create FastAPI app, add CORS middleware, attach routers, choose auth dependency, initialize SQLite schema, provide DB connection/session utilities.
- Non-Responsibilities: business logic of individual resources (delegated to routers/services), schema migrations/versioning beyond the hardcoded DDL, observability/logging, request-level auth logic (delegated to `auth_service.verify_token`).

## Dependencies & Integration Points
- Routers included from `app.api.routes.*` for all resources (`backend/app/main.py:4-19,52-65`).
- Auth dependency uses `auth_service.verify_token` when not in debug/skip-auth mode (`backend/app/main.py:45-50`).
- Settings loaded via `get_settings()` cached singleton (`backend/app/main.py:26`, `backend/app/config.py:62-64`).
- SQLite file location from `Settings.atlas_db_path`; path directories auto-created (`backend/app/db.py:11-15`).
- External libs: FastAPI, CORSMiddleware, Pydantic BaseSettings, sqlite3, jose JWT (via auth dependency).

## Interfaces & Contracts
- `create_app() -> FastAPI` (`backend/app/main.py:25-67`): constructs app, calls `init_db()`, configures CORS with `settings.allowed_origins`, conditionally enforces bearer auth dependency, registers routers under `/api` (streaming under `/api/stream`). Contract: safe to import for ASGI; idempotent DB init on startup.
- `Settings` (`backend/app/config.py:9-59`): fields for app_name, debug, skip_auth, allowed_origins, atlas_db_path, atlas_checkpoints_db_path, LLM backend & model settings, llama.cpp knobs, mode-specific parameters, auth_secret, qdrant_url. Contract: values come from env with prefix `CORTEX_`; defaults provided.
- `get_settings() -> Settings` (`backend/app/config.py:62-64`): lru_cache(1) to reuse settings across imports.
- `get_connection() -> sqlite3.Connection` (`backend/app/db.py:18-21`): opens connection to atlas DB with `check_same_thread=False`, row_factory set to sqlite3.Row. Callers must close or use session helper.
- `db_session()` context manager (`backend/app/db.py:24-30`): yields connection from `get_connection()` and closes afterward; no transaction management beyond caller commits.
- `init_db()` (`backend/app/db.py:33-350`): executes `PRAGMA journal_mode=WAL` and creates tables/indexes if missing. Contract: can be called repeatedly; no migration of existing schema.

## Data Models (from `init_db` DDL)
- `projects` (`backend/app/db.py:39-53`): core project entity; fields include `id` PK, `slug` unique, `status`, timestamps, optional `default_model_role_id`, `root_idea_cluster_id`, `roadmap_id`.
- `ingest_sources` (`54-66`): sources scoped to project with `kind`, `name`, optional `uri/description`.
- `ingest_jobs` (`67-88`): ingestion jobs linked to source/project; tracks file metadata, flags (`is_deep_scan` int as bool), `stage`, `progress`, `status`, timestamps, `completed_at`, `error_message`, `canonical_document_id`.
- `idea_tickets` (`89-103`): ticket records tied to project/cluster; `status`, `priority`, `origin_idea_ids_json` text for list.
- `knowledge_nodes` (`104-114`) and `knowledge_edges` (`310-325`): graph nodes/edges scoped to project; node `type`, edge `type/weight/label`.
- `agent_runs` (`115-127`), `agent_steps` (`182-197`), `agent_messages` (`199-209`), `agent_node_states` (`211-224`): track agent execution runs/steps/messages/node status with timestamps, statuses, and JSON blobs.
- `idea_candidates` (`128-143`) and `idea_clusters` (`145-156`): candidate ideas with embeddings, clusters linking ideas.
- `roadmaps` (`157-166`), `roadmap_nodes` (`273-292`), `roadmap_edges` (`294-308`): roadmap graph storage with statuses, dependencies, and lane/mission/task/ticket links.
- `context_items` (`168-180`): context artifacts with type, token count, pinned flag, optional canonical document link.
- `workflow_graphs` (`225-235`), `workflow_runs` (`237-257`), `workflow_node_states` (`259-271`): workflow definitions and runtime state with `status`, `progress`, messages JSON, checkpoints, pause/cancel timestamps.
- `gap_reports` (`327-334`), `gap_suggestions` (`335-347`): gap analysis outputs tied to project/report/ticket with confidence and related files JSON.

## Control Flows
- App startup: `create_app()` loads settings → `init_db()` ensures schema exists → FastAPI instantiated with title/version/docs paths → CORS middleware added with permissive methods/headers (`backend/app/main.py:25-44`) → auth dependency chosen based on `settings.debug` or `settings.skip_auth` (`45-50`) → routers registered with shared auth dependency (`52-65`).
- DB usage: callers use `db_session()` to acquire connection; `init_db()` runs once on app creation but is safe to re-run (no migration logic).

## Config & Runtime Parameters
- Auth toggle: `debug` and `skip_auth` env (`CORTEX_SKIP_AUTH`) influence whether auth dependency is enforced (`backend/app/main.py:45-50`).
- CORS: `allowed_origins` defaults to local dev hosts (`backend/app/config.py:13-19`).
- DB paths: `atlas_db_path`, `atlas_checkpoints_db_path` with defaults relative to working dir (`backend/app/config.py:21-22`).
- LLM: `llm_base_url`, `llm_api_key`, `llm_model_name`, `llm_backend`, llama.cpp binary/model path, context size, threads (`backend/app/config.py:24-42`).
- Execution modes: normal/paranoid temperatures, validation passes, max parallel tools (`backend/app/config.py:44-52`).
- Auth secret: `auth_secret` (`backend/app/config.py:54`); Qdrant URL (`backend/app/config.py:56-57`).

## Error & Failure Semantics
- Auth dependency raises 401 on invalid/missing token (`auth_service.verify_token`, noted here due to injection path in `backend/app/main.py:45-52`).
- `init_db()` swallows no errors; DB path creation uses `mkdir(parents=True, exist_ok=True)`; failure will propagate.
- No transaction management in `db_session()`; callers must commit/rollback; `init_db()` commits after DDL (`backend/app/db.py:35-350`).
- CORS allows all methods/headers; risk of over-exposure if deployed broadly.

## Observability
- No logging/metrics/tracing in app bootstrap, settings load, or DB helpers.
- No health checks or readiness endpoints at core level; relies on downstream routers.

## Risks, Gaps, and [ASSUMPTION] Blocks
- No migration/versioning; schema changes require manual coordination; existing data may break silently. [ASSUMPTION] Downstream services expect tables to exist exactly as defined; adding columns without migrations could fail inserts.
- Single shared `auth_secret` default is weak; no rotation/versioning. [ASSUMPTION] Production will override via env.
- CORS is wide open to any method/header; origins limited to local dev but may need tightening.
- `check_same_thread=False` enables cross-thread use without pooling; concurrency risks under load.
- Lack of observability/health endpoints makes startup and DB readiness opaque.
- DB stored at relative path by default; non-persistent in containerized deployments unless volumes configured.

## Verification Ideas
- Add integration test to assert `init_db()` creates all expected tables/indexes (inspect `sqlite_master`) and uses WAL mode.
- Test auth toggle: when `debug=True` or `skip_auth=True`, endpoints load without auth dependency; otherwise protected.
- Validate CORS config allows frontend origins and blocks others (if changed).
- Concurrency sanity: run simple parallel requests to confirm `check_same_thread=False` handling; consider sqlite busy scenarios.
- Add health endpoint to confirm DB connectivity after startup; monitor failure behavior if DB path unwritable.

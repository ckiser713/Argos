## Overview
- Project management: CRUD for Cortex projects with slug uniqueness and pagination (`backend/app/services/project_service.py:18-54`, `backend/app/api/routes/projects.py:18-57`, `backend/app/repos/project_repo.py:12-118`, `backend/app/domain/project.py:12-88`).
- Execution mode settings per project (normal/paranoid) stored in-memory with defaults from global settings (`backend/app/api/routes/mode.py:22-90`, `backend/app/repos/mode_repo.py:11-84`, `backend/app/domain/mode.py:7-46`).

## Responsibilities & Non-Responsibilities
- Responsibilities: create/list/get/update/delete projects; enforce slug uniqueness; map DB rows to domain models; expose per-project execution settings and allow updates of mode/LLM parameters.
- Non-Responsibilities: cascading deletes of dependent data (ideas/ingest/etc.); persistent storage for mode settings (currently in-memory); role-based access; project-level quotas/ownership checks.

## Dependencies & Integration Points
- DB: `projects` table (`backend/app/db.py:39-53`) via `db_session`.
- Domain models: `CortexProject`, requests/responses (`backend/app/domain/project.py`); `ProjectExecutionSettings` (`backend/app/domain/mode.py`).
- Config: default mode settings from `Settings` temperatures/validation/parallelism (`backend/app/config.py:44-52` via `mode_repo._build_default_settings`).
- HTTP: FastAPI routers under `/api/projects` and `/api/projects/{id}/mode`.

## Interfaces & Contracts
**Project APIs** (`backend/app/api/routes/projects.py`):
- `GET /api/projects` → `PaginatedResponse` with projects; supports `cursor`, `limit` (1–100) (`18-24`).
- `POST /api/projects` → 201 `CortexProject`; body `CreateProjectRequest {name, slug?, description?}` (`27-33`).
- `GET /api/projects/{project_id}` → `CortexProject` or 404 (`35-40`).
- `PATCH /api/projects/{project_id}` → `CortexProject`; body `UpdateProjectRequest` fields optional; 404 if missing (`43-49`).
- `DELETE /api/projects/{project_id}` → `DeleteProjectResponse {success}`; 404 if missing (`52-57`).

**Project service/repo**:
- `list_projects(cursor, limit)` paginates via LIMIT/OFFSET, returns next_cursor as string offset, total count (`backend/app/repos/project_repo.py:13-28`).
- `create_project` checks slug uniqueness via `get_by_slug`, raises 409 on conflict, builds project via `ProjectFactory` (`backend/app/services/project_service.py:31-37`).
- `update_project` whitelists updatable fields; raises 404/500 on missing/update failure (`backend/app/services/project_service.py:38-47`).
- `delete_project` returns success flag; raises 404 if not found (`backend/app/services/project_service.py:49-53`).

**Mode APIs** (`backend/app/api/routes/mode.py`):
- `GET /api/projects/{project_id}/mode` → `ProjectExecutionSettings`; builds defaults if absent (`22-32`).
- `PATCH /api/projects/{project_id}/mode` → updates mode/llm_temperature/validation_passes/max_parallel_tools; 400 if all fields null; persists in in-memory store (`34-90`).

**Mode repo** (`backend/app/repos/mode_repo.py`):
- `_PROJECT_SETTINGS_STORE` in-memory dict keyed by project_id; default built from global settings with mode "normal" unless specified (`11-51`).
- `set_project_settings` upserts and logs (`65-84`).

## Data Models
- `CortexProject {id, slug, name, description?, status (active|archived|draft), created_at, updated_at, default_model_role_id?, root_idea_cluster_id?, roadmap_id?}` (`backend/app/domain/project.py:18-55`).
- Requests: `CreateProjectRequest {name, slug?, description?}`, `UpdateProjectRequest {name?, description?, status?, default_model_role_id?, root_idea_cluster_id?, roadmap_id?}` (`backend/app/domain/project.py:33-49`).
- `ProjectExecutionSettings {project_id, mode normal|paranoid, llm_temperature, validation_passes, max_parallel_tools}` (`backend/app/domain/mode.py:10-46`).
- DB schema aligns with `projects` table (see backend-core data models).

## Control Flows
- Project creation: check slug uniqueness → build project with UUID + slugify(name) fallback → insert into DB → return.
- Project update: fetch existing; whitelist fields; update DB and updated_at; return refreshed record.
- Project deletion: DELETE by id; 404 if no row.
- Mode fetch: return cached settings or build defaults from global settings and cache.
- Mode update: reject empty body; merge provided fields into current settings; store in-memory; log change.

## Config & Runtime Parameters
- Mode defaults derived from `Settings.normal_*` and `Settings.paranoid_*` env vars (`backend/app/config.py:44-52`).
- Pagination limits 1–100; cursor is offset string.
- In-memory mode store resets on process restart; [ASSUMPTION] acceptable for dev.

## Error & Failure Semantics
- Slug conflict returns 409; missing project 404; update failure 500 (`project_service`).
- Mode PATCH with no fields returns 400; otherwise always succeeds (no DB errors possible).
- No referential integrity checks on delete; dependent data may remain orphaned.

## Observability
- Mode repo logs creation/update of settings; project service/repo do not log operations.
- No metrics or tracing.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Project delete does not cascade to dependent tables (ingest/jobs/ideas/etc.), leading to orphans. [ASSUMPTION] Cleanup deferred or handled elsewhere.
- Mode settings are in-memory only; lost on restart; no per-project persistence or concurrency control.
- No auth/ownership checks on project or mode routes beyond global dependency.
- Slug uniqueness check races possible (no DB constraint aside from unique index; OK for SQLite).

## Verification Ideas
- API tests for project CRUD: slug conflict returns 409; update respects whitelist; delete removes row.
- Integration test to ensure dependent resources handled (or document orphan behavior).
- Mode tests: GET returns defaults from settings; PATCH updates fields; empty PATCH returns 400; settings persist within process; reset behavior on restart documented.

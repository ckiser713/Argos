## Overview
- Ingest job management with SQLite persistence, file processing, optional RAG ingestion, and event emission (`backend/app/services/ingest_service.py:15-340`, `backend/app/api/routes/ingest.py:15-94`).
- Supports job listing/filtering (excluding soft-deleted), creation (including upload helper), cancellation, soft deletion, and background processing with streaming events.

## Responsibilities & Non-Responsibilities
- Responsibilities: create ingest jobs (auto-create default source), process files (read text/PDF), update job status/progress, emit ingest events, list/filter jobs, cancel/delete jobs (soft delete with `deleted_at`), keep project scoping.
- Non-Responsibilities: robust upload storage/validation, MIME/type detection, deduplication, multi-source handling, retry/resume, transactional deletions, cascade cleanup of related data, auth/scoping beyond project_id checks.

## Dependencies & Integration Points
- DB tables: `ingest_jobs`, `ingest_sources`, `schema_migrations` (`backend/app/db.py:54-104,244-255`).
- Domain models: `IngestJob`, `IngestStatus`, `IngestRequest`, `PaginatedResponse` (`backend/app/domain/models.py:111-142`, `backend/app/domain/common.py`).
- RAG ingestion via `rag_service.ingest_document` (errors swallowed) (`backend/app/services/ingest_service.py:231-235`).
- Event streaming via `emit_ingest_event` to WebSocket clients (`backend/app/services/ingest_service.py:136-139,177-183,246-255`).
- Upload helper writes to `temp_uploads/` then creates job (`backend/app/api/routes/ingest.py:82-94`).

## Interfaces & Contracts
**API endpoints** (`backend/app/api/routes/ingest.py`):
- `GET /api/projects/{project_id}/ingest/jobs` → `PaginatedResponse` with optional filters `status`, `stage`, `source_id`, `limit`, `cursor` (`15-31`).
- `GET /api/projects/{project_id}/ingest/jobs/{job_id}` → `IngestJob` or 404 if project mismatch (`34-39`).
- `POST /api/projects/{project_id}/ingest/jobs` → create job from `IngestRequest {source_path}`; schedules background `process_job`; 400 if missing source_path (`42-50`).
- `POST /api/projects/{project_id}/ingest/jobs/{job_id}/cancel` → cancel queued/running; 400 otherwise; 404 on mismatch (`53-67`).
- `DELETE /api/projects/{project_id}/ingest/jobs/{job_id}` → 204; 400 if RUNNING; 404 on mismatch (`69-79`).
- `POST /api/projects/{project_id}/ingest/upload` → multipart upload saved to temp path, creates job, schedules processing (`82-94`).

**Service methods** (`backend/app/services/ingest_service.py`):
- `list_jobs(project_id, cursor?, limit?, status?, stage?, source_id?) -> PaginatedResponse`: filters and paginates, excludes soft-deleted, returns next_cursor=id of extra row (`15-72`).
- `get_job(job_id)` → `IngestJob|None` (skips soft-deleted) (`74-79`).
- `create_job(project_id, IngestRequest)` → creates default ingest_source if none, inserts queued job with stage "initial", emits created event (`81-145`).
- `cancel_job(job_id)` → sets status CANCELLED, timestamps, emits event (`147-168`).
- `delete_job(job_id)` → soft delete: marks `deleted_at` and status CANCELLED; no cascade (`170-177`).
- `process_job(job_id)`: reads file (creates dummy file for tests if name contains "test-" or "temp"), processes PDF with pypdf if available, otherwise reads text; calls `rag_service.ingest_document`; sets COMPLETED or FAILED; emits events (`179-265`).
- `update_job(...)` → updates fields; preserves separate `message` vs `error_message`; emits job updated/completed/failed/cancelled events (`266-326`).

## Data Models
- `IngestJob {id, project_id?, source_path, original_filename?, byte_size?, mime_type?, stage?, created_at, updated_at?, completed_at?, deleted_at?, status queued|running|completed|failed|cancelled, progress 0..1, message?, error_message?, canonical_document_id?}` (`backend/app/domain/models.py:119-142`).
- DB columns include `is_deep_scan`, `source_id`, `byte_size`, `mime_type`, `canonical_document_id` (not all mapped in service responses).
- `IngestRequest {source_path}` (`backend/app/domain/models.py:144-146`).

## Control Flows
- Creation: ensure source exists or create default → insert job queued → emit created → schedule `process_job`.
- Processing: emit started → mark RUNNING → read file (create dummy for test names) → extract text (PDF via pypdf if installed) → attempt RAG ingest → mark COMPLETED with progress 1.0 or FAILED on errors → emit events.
- Cancellation: validate status (API) → set CANCELLED, completed_at, emit cancelled.
- Deletion: reject RUNNING at API layer; service marks `deleted_at` and sets status CANCELLED; no cascade.
- Listing: filter by project/status/stage/source; paginate by limit+1, next_cursor=id; excludes soft-deleted.

## Config & Runtime Parameters
- No configurable ingest roots or size limits; uses provided `source_path`.
- Uploads stored under `temp_uploads/` relative to cwd.
- RAG ingestion optional; errors ignored.
- Event emission uses asyncio tasks; no retries/backoff.

## Error & Failure Semantics
- API 404 on project mismatch; 400 on missing source_path or invalid cancel/delete state.
- `process_job` marks FAILED on file not found or read errors; may create dummy files for test-like names.
- `update_job` keeps `message` separate from `error_message` to avoid conflation.
- No transaction bundling across job/source creation and status updates.

## Observability
- Emits events but minimal logging; no metrics on processing duration or failure rates.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Hard delete with no cascade; canonical documents and embeddings remain orphaned. [ASSUMPTION] Cleanup deferred.
- Default source creation is implicit and non-configurable; no source kind/metadata beyond "file".
- `message` vs `error_message` conflated in `update_job` (both write error_message column).
- No size/type validation on uploads or source_path; potential security/operational issues.
- Dummy file creation logic could pollute filesystem in non-test contexts.
- No concurrency controls; multiple processors could race status updates.

## Verification Ideas
- API tests: create/cancel/delete flows with status validation; ensure RUNNING delete blocked; project scoping enforced.
- Service tests: `process_job` with missing file yields FAILED; PDF path without pypdf sets placeholder message; message/error fields persist correctly after `update_job` bug fix.
- RAG integration test stub: verify `rag_service.ingest_document` called with expected text/metadata (mock).
- Upload test: multipart upload creates job and schedules processing; temp file cleanup validated.

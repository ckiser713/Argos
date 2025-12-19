## Overview
- Ingest jobs are persisted in Postgres/SQLite and processed by a Celery worker queue. Uploads are stored durably (S3/MinIO or local dev path) with checksum + content-type/size validation before job creation. (`backend/app/services/ingest_service.py`, `backend/app/api/routes/ingest.py`)
- Supports listing/filtering (excluding soft-deleted), creation via direct source URI or multipart upload, cancellation, soft deletion, and streamed status updates.

## Responsibilities & Non-Responsibilities
- Responsibilities: create ingest jobs (auto-create default source), upload to durable storage, enqueue Celery task, process files/repos, update status/progress/error, emit ingest events, list/filter jobs, cancel/delete jobs (soft delete with `deleted_at`), keep project scoping.
- Non-Responsibilities: deduplication/content-addressing, lifecycle/retention of embeddings, cascade cleanup of downstream artifacts, auth beyond project_id checks, resumable uploads.

## Dependencies & Integration Points
- DB tables: `ingest_jobs`, `ingest_sources`, `schema_migrations` (+ new columns via migration `003_ingest_durable_pipeline`).
- Domain models: `IngestJob`, `IngestStatus`, `IngestRequest`, `PaginatedResponse`.
- Storage: `storage_service` (boto3 S3/MinIO or local) handles upload/download + checksum/size/type validation.
- Queue: Celery task `process_ingest_job_task` (`app/tasks/ingest_tasks.py`) invoked via `ingest_service.enqueue_job`; uses Redis broker/result backend by default.
- RAG ingestion via `rag_service.ingest_document`; failure returns 0 chunks but processing still completes.
- Event streaming via `emit_ingest_event` to WebSocket clients (currently best-effort).

## Interfaces & Contracts
**API endpoints** (`backend/app/api/routes/ingest.py`):
- `GET /api/projects/{project_id}/ingest/jobs` → `PaginatedResponse` with optional filters `status`, `stage`, `source_id`, `limit`, `cursor`.
- `GET /api/projects/{project_id}/ingest/jobs/{job_id}` → `IngestJob` or 404 if project mismatch.
- `POST /api/projects/{project_id}/ingest/jobs` → create job from `IngestRequest {source_uri|source_path,...}`; enqueues Celery task; 400 if missing source.
- `POST /api/projects/{project_id}/ingest/jobs/{job_id}/cancel` → cancel queued/running; 400 otherwise; 404 on mismatch.
- `DELETE /api/projects/{project_id}/ingest/jobs/{job_id}` → 204; 400 if RUNNING; 404 on mismatch.
- `POST /api/projects/{project_id}/ingest/upload` → multipart upload stored to durable storage, job created with checksum/size/content-type metadata, enqueued for processing.
- `POST /api/projects/{project_id}/ingest` → simple helper for tests (text/repo); now also stores text payload via storage_service and enqueues Celery.

**Service methods** (`backend/app/services/ingest_service.py`):
- `list_jobs(project_id, cursor?, limit?, status?, stage?, source_id?) -> PaginatedResponse`: SQLAlchemy query excluding soft-deleted; returns `next_cursor=id` when more rows.
- `get_job(job_id)` → `IngestJob|None` (skips soft-deleted).
- `create_job(project_id, IngestRequest)` → ensures default ingest_source, stores checksum/size/mime, queues status=queued.
- `enqueue_job(job_id)` → Celery `apply_async` (non-local) or inline retry loop (eager mode).
- `cancel_job(job_id)` / `delete_job(job_id)` → status updates + soft delete.
- `process_job(job_id, mark_failed=True)` → downloads from storage when needed, checksum verifies, detects doc type with LLM (when configured), indexes repos/files, updates progress/status, optional retries handled by queue wrapper.
- `update_job(...)` → SQLAlchemy status/progress/message/error/start/completion fields; emits events best-effort.

## Data Models
- `IngestJob {id, project_id?, source_path?, source_uri?, original_filename?, byte_size?, mime_type?, checksum?, stage?, created_at, updated_at?, started_at?, completed_at?, deleted_at?, task_id?, status queued|running|completed|failed|cancelled, progress 0..1, message?, error_message?, canonical_document_id?}`
- `IngestRequest {source_uri?, source_path?, original_filename?, mime_type?, byte_size?, checksum?}` (validator requires at least source_uri/source_path).

## Control Flows
- Creation: upload (if multipart) → durable URI + checksum/size/type → ensure ingest_source → insert queued job → enqueue Celery (records task_id) → worker runs `process_job`.
- Processing: mark RUNNING + started_at → download/validate checksum → repo indexing or file extraction → optional LLM metadata/chat parsing → RAG ingest → mark COMPLETED (or FAILED on final attempt). Retries handled by Celery autoretry/backoff or eager inline loop.
- Cancellation: validate status (API) → set CANCELLED, completed_at.
- Deletion: reject RUNNING at API layer; service marks `deleted_at` and sets status CANCELLED.
- Listing: filter by project/status/stage/source; paginate by limit+1, next_cursor=id; excludes soft-deleted.

## Config & Runtime Parameters
- Storage: `CORTEX_STORAGE_BACKEND` (s3|local), `CORTEX_STORAGE_BUCKET`, `CORTEX_STORAGE_ENDPOINT_URL`, `CORTEX_STORAGE_ACCESS_KEY/SECRET_KEY`, `CORTEX_STORAGE_SECURE`, `CORTEX_STORAGE_PREFIX`, `CORTEX_STORAGE_LOCAL_DIR`, `CORTEX_STORAGE_MAX_UPLOAD_MB`, `CORTEX_STORAGE_ALLOWED_CONTENT_TYPES`.
- Queue: `CORTEX_CELERY_BROKER_URL`, `CORTEX_CELERY_RESULT_BACKEND`, `CORTEX_TASKS_EAGER` (true by default in local/tests), `CORTEX_TASK_MAX_RETRIES`, `CORTEX_TASK_RETRY_BACKOFF_SECONDS`, `CORTEX_TASK_RETRY_BACKOFF_MAX_SECONDS`.
- RAG ingestion optional; errors ignored.
- Event emission best-effort; no guaranteed delivery.

## Error & Failure Semantics
- API 404 on project mismatch; 400 on missing source or invalid cancel/delete state.
- Upload validation: rejects oversized or disallowed content types; checksum stored and enforced on download.
- Retries: Celery backoff + max retries; eager mode uses inline retries without sleeping.
- Failures propagate to job status FAILED with error_message.

## Observability
- Logging around storage, retries, and RAG ingest; events emitted when update_job succeeds. Metrics/tracing still minimal.

## Risks, Gaps, and [ASSUMPTION] Blocks
- No deduplication or retention policy for stored objects/embeddings. [ASSUMPTION] External lifecycle/cleanup.
- Default source creation is implicit; no per-source auth/metadata.
- No checksum revalidation on long-term reuse beyond initial download.
- No concurrency controls; multiple workers could race updates on the same job id (status writes last-wins).

## Verification Ideas
- API tests: upload job captures checksum/size/mime + completes; polling reflects queued→running→completed; cancel/delete flows enforced.
- Retry test: force first attempt failure; ensure job retries and completes; final failure marks status FAILED with error_message.
- Storage validation: disallowed MIME/oversized file returns 400.

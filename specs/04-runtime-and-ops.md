## Run Modes & Processes
- Backend: FastAPI app (`app.main:app`) run via uvicorn; initializes SQLite schema on startup (`init_db`, stamps `schema_migrations`).
- Frontend: Vite dev server for React app; production build not detailed.
- Background tasks: ingest now offloaded to Celery worker queue (Redis broker, eager inline mode in local/tests); other long-running flows still rely on asyncio tasks.
- Streaming: WebSocket endpoints under `/api/stream/...` and SSE endpoints; WebSockets rely on event broadcasts (no DB polling) and enforce per-project connection caps and send timeouts.
- Guardrail: All local development should occur inside the Nix dev shells (`nix develop` or `nix-shell nix/rocm-shell.nix`); scripts should invoke `tools/require-nix.sh` to prevent running outside Nix or ad-hoc virtualenvs.

## Configuration & Environment
- Settings via env (prefix `CORTEX_`): auth secret, debug/skip_auth, allowed_origins, DB paths (`atlas.db`, `atlas_checkpoints.db`), LLM backend/config (`llm_base_url`, `llm_api_key`, `llm_model_name`, `llm_backend`, llama.cpp paths/threads/context), mode parameters (normal/paranoid temps, validation passes, max_parallel_tools), qdrant_url, queue (`CORTEX_CELERY_BROKER_URL`, `CORTEX_CELERY_RESULT_BACKEND`, `CORTEX_TASKS_EAGER`), storage (`CORTEX_STORAGE_*` for S3/MinIO/local).
- Hardcoded defaults: context token budget 100k; local ingest storage path `storage_uploads` when `CORTEX_STORAGE_BACKEND=local`; Qdrant URL in `rag_service` fixed to `http://localhost:6333`; RAG model all-MiniLM-L6-v2.
- No env/config for streaming, timeouts, rate limits beyond hardcoded caps/timeouts in `ConnectionManager`.

## Dependencies
- SQLite (local file with WAL).
- Qdrant (optional; required for vector search/RAG).
- OpenAI-compatible API or local llama.cpp binary.
- SentenceTransformers model download at runtime.

## Operational Concerns
- Migration/version tracking is lightweight (schema version table) but lacks upgrade tool.
- Liveness/readiness: `/api/system/health` returns ok; `/api/system/ready` verifies DB connectivity.
- Logging minimal; no metrics/tracing.
- Auth: `/api/token` issues JWT for any credentials; `skip_auth` toggles dependency; streaming routes inherit global auth deps.
- File handling: uploads validated and stored via storage_service; retention/cleanup policy for objects/embeddings not defined.
- Streaming: WebSockets are event-driven; SSE remains polling-based. Backpressure limited to connection caps/timeouts.
- Mode settings for projects stored in-memory; lost on restart.

## Performance & Scalability
- SQLite single-writer; `check_same_thread=False` permits multi-thread use but no pooling/backoff.
- Background tasks may overlap writes; no concurrency limits on ingest/agent/workflow execution.
- Qdrant/LLM calls synchronous; no timeouts/retries in RAG; agent execution now has basic retry/backoff/timeout.

## Reliability & Recovery
- Agent execution retries/backoff/timeout; other services still lack retries.
- No checkpoint/resume beyond workflow pause fields; ingest/workflow processing not idempotent.
- No backup/restore strategy for SQLite or Qdrant data.

## Security
- Bearer auth optional; `/api/token` unvalidated; streaming inherits auth deps but relies on global setting.
- No input validation/sanitization for file uploads or source paths; potential path issues.
- Secrets loaded via env; single static secret; no rotation.

## Suggested Operational Tasks
- Add migration tool (e.g., Alembic) for schema evolution beyond current version stamp.
- Add metrics/tracing and structured logging around ingest/agent/workflow pipelines.
- Configure timeouts/retries for RAG/LLM/DB writes; move streaming to event-driven updates.
- Harden auth: validate credentials at /api/token, enforce auth consistently, rotate secrets.
- Define storage paths/config for uploads, cleanup/retention policy.
- Persist project mode settings; add admin endpoints for ops toggles.

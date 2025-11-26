## Overview
- LLM service abstraction supporting OpenAI-compatible backends and optional local llama.cpp, with paranoid-mode validation and project-specific settings (`backend/app/services/llm_service.py:1-166`).
- RAG service for embedding documents into Qdrant using SentenceTransformers and vector search (`backend/app/services/rag_service.py:1-49`).

## Responsibilities & Non-Responsibilities
- Responsibilities: generate text with temperature/validation based on project mode; select backend (OpenAI/vLLM/Ollama vs llama.cpp); support JSON-mode responses; provide simple document ingest and vector search via Qdrant.
- Non-Responsibilities: prompt management, rate limiting, retries, auth enforcement, embedding/schema migrations, collection lifecycle beyond initial create, streaming responses.

## Dependencies & Integration Points
- Settings: `llm_base_url`, `llm_api_key`, `llm_model_name`, `llm_backend`, llama.cpp paths, mode settings (`backend/app/config.py`); project-specific settings via `mode_repo.get_project_settings`.
- Backends: OpenAI-compatible API via `openai.OpenAI` client; optional `llama_cpp_service` for local generation.
- RAG: `qdrant_client` and `sentence_transformers` (all-MiniLM-L6-v2), collection `cortex_vectors` at `http://localhost:6333`.
- Consumers: roadmap intent generation, gap analysis notes, project manager graph tools, etc.

## Interfaces & Contracts
- `generate_text(prompt, project_id, base_temperature, max_tokens=500, model="default_llm", json_mode=False, **extra)` → string (`backend/app/services/llm_service.py:95-166`): fetches project settings, sets temperature, calls `_call_underlying_llm`, applies paranoid validation passes if mode=paranoid.
- `_call_underlying_llm(...)` selects backend based on `settings.llm_backend`: llama_cpp branch calls `llama_cpp_service.generate`; OpenAI branch uses `client.chat.completions.create` with optional `response_format` for JSON (`26-93`).
- `get_llm_client()` returns OpenAI client (`22-24`).
- RAG: `RagService.ingest_document(text, metadata)` chunks text (500 chars, 50 overlap), embeds, upserts to Qdrant (`28-42`); `search(query, limit=5)` returns list of {content, score} dicts from Qdrant (`43-47`).

## Data Models
- ProjectExecutionSettings control temperature/validation/max_parallel_tools (see backend-projects-and-mode spec).
- RAG collection vectors size 384, cosine distance; payload includes content + metadata.

## Control Flows
- LLM: choose backend → generate raw response; in paranoid mode, run `validation_passes` checker prompts at low temp to refine answer; return validated result.
- Llama.cpp path falls back to OpenAI if import/errors; JSON extraction heuristic for llama_cpp in json_mode.
- RAG: on init, attempt to create collection if missing; on ingest, chunk→embed→upsert; on search, embed query and run Qdrant search.

## Config & Runtime Parameters
- Backend switch via `CORTEX_LLM_BACKEND` ("openai" default, "llama_cpp"); model name from settings.
- Paranoid mode parameters from settings (validation_passes, temperature clamp); max_tokens default 500.
- RAG Qdrant endpoint hardcoded `http://localhost:6333`; model fixed to all-MiniLM-L6-v2; collection name `cortex_vectors`.

## Error & Failure Semantics
- OpenAI/llama_cpp errors logged; `_call_underlying_llm` returns "LLM Error: ..." string on OpenAI exception.
- RAG init swallows exceptions (logs warning) if Qdrant unavailable; ingest/search will raise if client absent.
- No retries/backoff; no rate limiting; no input sanitization.

## Observability
- LLM service logs generation start and paranoid passes; errors logged on backend failures.
- RAG service logs only on initialization failure (warning); no metrics/traces.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Hardcoded Qdrant URL/model/collection; no multi-tenant or per-project collections; [ASSUMPTION] single collection acceptable.
- No auth/timeouts for LLM calls; potential hangs or quota issues.
- Paranoid validation reuses same model; may not truly validate.
- RAG ingest lacks batching limits and error handling; could fail silently if Qdrant down.
- JSON-mode heuristic for llama_cpp may produce invalid JSON.

## Verification Ideas
- Tests: mock OpenAI client to verify temperature/model/json_mode selection; paranoid mode runs checker passes; llama_cpp fallback behavior.
- RAG tests with mocked Qdrant client to ensure collection init, ingest chunking, and search mapping; handle unavailable client gracefully.
- Performance: add timeouts/retries and test failure paths; make Qdrant URL/configurable and validate via integration test.

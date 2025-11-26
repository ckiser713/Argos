## System Goals & Scope
- Cortex provides a FastAPI backend with SQLite persistence for projects, ingest, knowledge graph, workflows, agents, ideas/tickets/roadmap, and gap analysis, plus a React/Vite frontend and Playwright e2e suite.
- Primary flows: project creation → ingest documents → build knowledge graph → run agents/workflows → manage ideas/tickets/roadmap → perform gap analysis; with streaming updates over WebSockets/SSE.
- External dependencies: OpenAI-compatible LLM (or llama.cpp), Qdrant vector store (optional/fallback), SentenceTransformers embeddings (RAG), SQLite databases (atlas.db), WebSocket clients for streaming.

## End-to-End Data Flows
- **Ingest**: Client calls `/api/projects/{pid}/ingest/jobs` → IngestService writes `ingest_jobs` and optional `ingest_sources` → background processing reads file, optionally ingests to Qdrant via `rag_service`, updates job status, emits events → frontend consumes events or polls.
- **Knowledge**: CRUD nodes/edges under `/api/knowledge` (project-scoped) → stored in `knowledge_nodes/edges`; vector embeddings upserted to Qdrant; search uses Qdrant then text fallback.
- **Workflows**: Workflow graphs stored in `workflow_graphs`; runs stored in `workflow_runs`/`workflow_node_states`; execution via LangGraph stub; events emitted via `emit_workflow_event`.
- **Agents**: Agent runs stored in `agent_runs/steps/messages/node_states`; execution via LangGraph project_manager_graph using LLM/tools; streaming via `emit_agent_event`.
- **Ideas/Tickets/Roadmap**: Idea candidates/clusters/tickets/tasks in `idea_candidates`, `idea_clusters`, `idea_tickets`; roadmap nodes/edges in `roadmap_nodes/edges`; mission-control tasks layered on tickets.
- **Gap Analysis**: Uses project intel tickets → code search (adapter) → LLM notes → stores gap_reports/gap_suggestions.
- **Context**: Context items per project with token budget; affects agent/workflow context items (indirect).

## External Services & Constraints
- LLM: `CORTEX_LLM_BACKEND` selects OpenAI-compatible vs llama.cpp; `llm_base_url`/`llm_api_key` required for OpenAI path.
- Qdrant: expected at `http://localhost:6333`; optional, search falls back to DB LIKE if unavailable.
- Embeddings: SentenceTransformers model download required; local CPU/GPU load considerations.
- SQLite: single-file DB at `atlas.db`; WAL enabled, `check_same_thread=False`; no migrations.

## Users & Actors
- API clients (frontend, tests) acting as a single trust domain (no RBAC); bearer auth available but /api/token accepts any credentials (test/demo).
- Operators running backend (uvicorn) and frontend (Vite) locally; e2e tests via Playwright.

## [ASSUMPTION] Notes
- Assumes single-tenant deployment with permissive CORS; production hardening not yet defined.
- Assumes streaming clients authenticate via global dependency; streaming routes currently unauthenticated in code.

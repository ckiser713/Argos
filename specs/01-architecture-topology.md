## Components & Relationships
- **Backend (FastAPI)**: Entry `backend/app/main.py` loads settings, initializes SQLite schema, attaches routers for auth, projects, context, ingest, knowledge, agents, workflows, gap-analysis, roadmap, ideas, streaming.
- **Services/Repos**: Business logic in `backend/app/services/*`, persistence helpers in `backend/app/repos/*`, domain models in `backend/app/domain/*`.
- **Datastores**: SQLite (`atlas.db`) for all domain tables; Qdrant for vector search (knowledge, RAG); optional embeddings model.
- **Execution Engines**: LangGraph used by workflow_service and project_manager_graph for agents; LLM service abstracts OpenAI/llama.cpp; RAG service wraps SentenceTransformers + Qdrant.
- **Frontend (React/Vite)**: UI shell and feature components; hooks call backend APIs; Zustand store for state.
- **Streaming**: WebSocket/SSE via `streaming_service` and `/api/stream` routes; emits ingest/agent/workflow events.
- **E2E Tests**: Playwright suite against deployed frontend/backend.

## Deployment Topology
- Expected local/dev: single FastAPI process (uvicorn) + SQLite file; optional Qdrant instance; frontend served separately (Vite dev server) hitting `/api`.
- No container/orchestration manifests in repo beyond `ops/docker-compose.yml` (qdrant/vLLM).
- No horizontal scaling; SQLite with `check_same_thread=False`; WebSockets handled in-process.

## Failure Domains & Boundaries
- Backend crash affects all APIs/streams; SQLite single point; Qdrant optional but search/embedding operations fail/skip if unavailable.
- Streaming backpressure unmanaged; many WebSocket clients could affect process.
- LLM backend errors logged; generate_text returns error string; downstream must handle.
- RAG ingestion/search depends on Qdrant availability; failures may be silent (warnings only).

## Interactions
- HTTP: REST endpoints under `/api` for all resources; streaming under `/api/stream/...` WebSockets and some SSE endpoints.
- Events: `emit_ingest_event`, `emit_agent_event`, `emit_workflow_event` push JSON to connected sockets per project.
- Background tasks: FastAPI BackgroundTasks/asyncio create_task used for ingest processing, workflow execution, agent execution.

## [ASSUMPTION] Notes
- Production topology not defined; assume single-node deployment for now.
- Auth boundaries minimal; all APIs share same trust unless skip_auth enabled.

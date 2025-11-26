## Overview
- Agent orchestration: predefined agent profiles, persistent agent run/step/message/node-state storage in SQLite, LangGraph-driven execution, and lifecycle APIs (`backend/app/services/agent_service.py:28-610`, `backend/app/api/routes/agents.py:25-172`).
- Real-time streaming: WebSocket/SSE infrastructure and emitters for ingest, agent, and workflow events (`backend/app/services/streaming_service.py:12-124`, `backend/app/api/routes/streaming.py:26-235`).
- Supporting LangGraph agent graph with tools for RAG search, roadmap creation, and n8n workflow triggers (`backend/app/graphs/project_manager_graph.py:1-119`).
- Agent domain models for runs/steps/messages/node states (`backend/app/domain/models.py:141-225`) and DB schema for `agent_runs`, `agent_steps`, `agent_messages`, `agent_node_states` (`backend/app/db.py:115-224`).

## Responsibilities & Non-Responsibilities
- Responsibilities: expose agent profiles; create/track agent runs; append/list steps/messages/node states; execute runs over LangGraph; emit events for clients; manage WebSocket connections and broadcast events; SSE endpoints for ingest/agent streams.
- Non-Responsibilities: user authentication/authorization; robust agent tooling (limited to stub LangGraph graph); durable job scheduling or retries; schema migrations; validation of project/agent definitions beyond simple presence.

## Dependencies & Integration Points
- SQLite access via `db_session()` for all CRUD (`backend/app/services/agent_service.py:57-420`).
- LangGraph graph `project_manager_graph` for agent execution and SSE streaming (`backend/app/api/routes/agents.py:16`, `backend/app/services/agent_service.py:430-519`).
- Tools inside graph call `rag_service.search` and `create_roadmap_nodes_from_intent`, plus n8n trigger (`backend/app/graphs/project_manager_graph.py:4-35`).
- LLM client `ChatOpenAI` configured from settings (`backend/app/graphs/project_manager_graph.py:60-69`).
- Event emission to WebSocket clients via `emit_agent_event`/`emit_workflow_event` and `connection_manager` (`backend/app/services/agent_service.py:144-177,340-345`, `backend/app/services/streaming_service.py:12-124`).
- Streaming endpoints rely on `ingest_service`, `agent_service`, and `connection_manager` (`backend/app/api/routes/streaming.py:26-235`).
- Domain models `AgentRun`, `AgentStep`, `AgentMessage`, `AgentNodeState`, `AgentRunRequest`, enums for statuses/roles (`backend/app/domain/models.py:141-225`).

## Interfaces & Contracts
**Agent APIs** (`backend/app/api/routes/agents.py`):
- `GET /api/agents/profiles` → List `AgentProfile` (`25-28`).
- `GET /api/agents/profiles/{agent_id}` → Single profile or 404 (`30-35`).
- `GET /api/projects/{project_id}/agent-runs` → List runs scoped to project (`38-42`).
- `GET /api/projects/{project_id}/agent-runs/{run_id}` → Run by id, 404 if project mismatch (`44-49`).
- `POST /api/projects/{project_id}/agent-runs` → Start run; body `AgentRunRequest` must match path project_id; 404 if agent missing; schedules background execution (`52-67`).
- `GET /api/projects/{project_id}/agent-runs/{run_id}/steps|messages` → PaginatedResponse; 404 on missing/mismatched run (`70-104`).
- `POST /api/projects/{project_id}/agent-runs/{run_id}/messages` → Append user message; if run completed, resets to pending; 404/400 checks (`106-127`).
- `GET /api/projects/{project_id}/agent-runs/{run_id}/node-states` → List node states (`129-143`).
- `POST /api/projects/{project_id}/agent-runs/{run_id}/cancel` → Cancel pending/running run; 400 otherwise (`145-158`).
- `GET /api/projects/{project_id}/agent-runs/{run_id}/stream` → SSE stream of LangGraph events from `project_manager_graph` using stored input_prompt (`160-172`).

**Agent service** (`backend/app/services/agent_service.py`):
- Profile registry in-memory (`36-49`).
- Run lifecycle: `list_runs`, `get_run`, `create_run_record` (inserts PENDING run), `update_run` (status/output updates, emits events), `cancel_run` (set CANCELLED, emit) (`57-179`).
- Steps/messages/node states: `list_steps`, `create_step`, `update_step`; `list_messages`, `append_message` (emits `agent.message.appended`); `list_node_states`, `update_node_state` (upsert with timestamps) (`181-420`).
- Execution: `execute_run(run_id)` loads LangGraph app, seeds node state, streams events to update node states and emit events, awaits final invoke to set COMPLETED or FAILED (`422-523`).
- Row mappers parse JSON blobs to domain models (`524-608`).

**Streaming infrastructure**:
- `ConnectionManager` manages project-scoped WebSockets with lock (`backend/app/services/streaming_service.py:12-66`).
- Emitters: `emit_ingest_event`, `emit_agent_event`, `emit_workflow_event` broadcast JSON with timestamp and optional payloads (`69-124`).
- WebSocket endpoints: ingest job stream (`/api/stream/projects/{project_id}/ingest/{job_id}`) polls ingest_service; agent run stream polls run/steps/messages/node states; workflow node stream reuses agent node states as proxy (`backend/app/api/routes/streaming.py:26-235`).
- SSE endpoint for ingest job events (`82-112`) and agent run stream (`160-172` in agents router).

**Graph** (`backend/app/graphs/project_manager_graph.py`):
- Tools: `search_knowledge` → `rag_service.search`; `create_roadmap` → `create_roadmap_nodes_from_intent`; `trigger_n8n_workflow` imported tool (`17-52`).
- LLM: `ChatOpenAI` with settings, streaming enabled (`60-69`); bound tools.
- StateGraph nodes: `agent` selects tool calls, `tools` executes tools via executor; conditional edges loop until no tool calls; compiled app exported (`72-119`).

## Data Models
- `AgentProfile {id, name, description?, capabilities[]}` (`backend/app/domain/models.py:144-149`).
- `AgentRun {id, project_id, workflow_id?, agent_id, status (pending|running|completed|failed|cancelled), input_prompt?, output_summary?, context_item_ids[], started_at, finished_at?}` (`backend/app/domain/models.py:159-171`, DB `agent_runs` `backend/app/db.py:115-127`).
- `AgentStep {id, run_id, step_number, node_id?, status (pending|running|completed|failed), input?, output?, error?, duration_ms?, started_at, completed_at?}` (`backend/app/domain/models.py:180-199`, DB `agent_steps` `backend/app/db.py:182-197`).
- `AgentMessage {id, run_id, role (user|assistant|system), content, context_item_ids[], created_at}` (`backend/app/domain/models.py:201-214`, DB `backend/app/db.py:199-209`).
- `AgentNodeState {run_id, node_id, status, progress [0-1], messages[], started_at?, completed_at?, error?}` (`backend/app/domain/models.py:216-224`, DB `backend/app/db.py:211-224`).
- PaginatedResponse from `domain.common` used for steps/messages listing (`backend/app/api/routes/agents.py:71-104`).

## Control Flows
- **Run creation & execution**: POST run → `create_run_record` inserts PENDING run → background task `execute_run` sets RUNNING, streams LangGraph events updating node states and emitting events, then `ainvoke` to completion sets COMPLETED with `output_summary`; exceptions set FAILED and node failed (`backend/app/services/agent_service.py:74-178,422-523`).
- **Messaging**: append_message inserts message, emits `agent.message.appended` (`310-345`); list endpoints paginate.
- **Cancellation**: cancel_run sets CANCELLED with timestamp; API blocks cancel on terminal states (`145-158`, `158-179`).
- **Streaming**: WebSocket connect registers project, polls services, sends JSON events, cleans up on disconnect/errors (`backend/app/api/routes/streaming.py:26-235`); SSE endpoint for agent run uses LangGraph events directly (`backend/app/api/routes/agents.py:160-172`).
- **Graph execution**: StateGraph nodes call tools or finish; tools may modify roadmap or query RAG; tool executor injects project_id for roadmap tool (`backend/app/graphs/project_manager_graph.py:72-118`).

## Config & Runtime Parameters
- LLM config from settings (`llm_model_name`, `llm_base_url`, `llm_api_key`) used by ChatOpenAI (`backend/app/graphs/project_manager_graph.py:60-69`).
- WebSocket broadcasting uses shared `connection_manager`; no auth gating beyond global dependencies in app router.
- No explicit timeouts/backoff in streaming polling loops (1s sleep).

## Error & Failure Semantics
- API returns 404 for missing agent/run/step/message; 400 on project mismatch or invalid status for cancel; 422 on body validation (Pydantic) — note `AgentRunRequest` requires `project_id` but tests omit it. [ASSUMPTION] Clients must supply `project_id` in body; otherwise request fails.
- Agent profiles limited to `"researcher"` and `"planner"` (`backend/app/services/agent_service.py:36-49`); route rejects unknown agent ids; tests/use of `"project_manager"` will 404.
- `execute_run` swallows missing run (returns None) and logs failure via update_run on exceptions; event emission is fire-and-forget with `asyncio.create_task` (errors not surfaced).
- Streaming endpoints poll DB/services; if job/run disappears, stream ends silently; errors send `stream_error` and close (`backend/app/api/routes/streaming.py:67-78,227-234`).
- Node state updates in `update_node_state`/`update_step` do not enforce transactionality with run updates; partial states possible.

## Observability
- Logging namespaces `cortex.streaming` and LangGraph execution logs, but minimal structured data (`backend/app/services/streaming_service.py:9`, `backend/app/graphs/project_manager_graph.py:71-125`).
- Events broadcast over WebSockets include `type`, timestamp, and payload; no metrics/traces.
- No health or audit logging for connection lifecycle beyond info logs.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Agent profile mismatch: only `researcher`/`planner` defined but API tests/reference `project_manager`; run creation will 404. Needs alignment or expanded profiles.
- `AgentRunRequest` requires `project_id` in body, but API callers/tests omit it → 422/400 on mismatch; [ASSUMPTION] clients should include project_id or adjust schema.
- LangGraph execution uses external LLM and tools (RAG, roadmap creation) with no error isolation; failures mark run failed without retries.
- Streaming endpoints poll every second and broadcast whole payloads; no throttling/backpressure handling.
- WebSocket connections keyed only by project_id; no authentication inside streaming routes; [ASSUMPTION] upstream auth dependency covers websockets.
- Node states and steps can diverge from LangGraph events (manual inserts vs event-driven); no ordering guarantees.
- SSE endpoint for agent runs ignores DB state and replays live LangGraph events, potentially desynchronized from stored run execution.

## Verification Ideas
- API contract tests: ensure POST agent-run with missing/incorrect project_id returns 400/422; add successful case with correct body and known agent id; verify run stored and returned.
- Seed known agent profile (e.g., project_manager) or adjust tests; add test asserting 404 for unknown agent id.
- Execution integration: run create→execute→poll node states/messages; assert run status transitions RUNNING→COMPLETED and events emitted (inject test connection manager).
- Streaming tests: mock ingest_service/agent_service to validate WebSocket/SSE event payloads and lifecycle (connect, initial state, update, close on terminal status).
- Persistence tests: insert node states/steps/messages with JSON blobs, verify mappers correctly parse context_item_ids/messages and pagination returns next_cursor/total.

## Overview
- Workflow orchestration service that stores workflow graphs/runs in SQLite, executes graphs via LangGraph, and exposes lifecycle APIs for creation, execution, cancellation, pause/resume, and status (`backend/app/services/workflow_service.py:31-612`, `backend/app/api/routes/workflows.py:25-184`).
- Workflow graph compiler translating stored graph nodes/edges into a LangGraph `StateGraph`, providing stub node execution logic and state tracking hooks (`backend/app/services/workflow_compiler.py:25-200`).
- Domain models define workflow graph/run/node state schemas used across service and API (`backend/app/domain/models.py:52-107`).

## Responsibilities & Non-Responsibilities
- Responsibilities: persist workflow graphs/runs/node states; orchestrate execution over LangGraph; emit workflow events to streaming layer; expose REST endpoints for listing graphs, managing runs, executing, cancelling, pausing/resuming, and reporting status.
- Non-Responsibilities: graph authoring endpoint/UI (no route to create/update graphs); durable task scheduling beyond background tasks; access control; schema migrations/versioning; rich node/tool semantics (execution logic is stubbed).

## Dependencies & Integration Points
- SQLite via `db_session()` for CRUD on `workflow_graphs`, `workflow_runs`, and `workflow_node_states` tables (`backend/app/services/workflow_service.py:31-301`).
- Domain models `WorkflowGraph/Node/Edge/Run/RunStatus/NodeState/NodeStatus` (`backend/app/domain/models.py:52-107`).
- Streaming events emitted through `emit_workflow_event` (WebSocket broadcast) (`backend/app/services/workflow_service.py:189-197`, `288-294`, `328-378`, `385-403`).
- LangGraph `StateGraph` used to compile and execute workflows (`backend/app/services/workflow_compiler.py:37-63`, `backend/app/services/workflow_service.py:337-369`).
- API router exposes project-scoped workflow endpoints (`backend/app/api/routes/workflows.py:25-184`); relies on FastAPI `BackgroundTasks` for async execution kickoff.
- [ASSUMPTION] Graph content originates from elsewhere (no create/update route); likely seeded externally or via direct DB edits.

## Interfaces & Contracts
**Service methods** (`backend/app/services/workflow_service.py`):
- `list_graphs(project_id: Optional[str]) -> List[WorkflowGraph]` (`31-38`): fetch graphs (optionally filtered by project).
- `get_graph(workflow_id: str) -> Optional[WorkflowGraph]` (`39-44`): fetch graph by id.
- `create_graph(project_id: str, graph_data: dict) -> WorkflowGraph` (`46-87`): construct WorkflowGraph from `graph_data` nodes/edges and persist JSON; not exposed via API.
- `list_runs(project_id?: str, workflow_id?: str) -> List[WorkflowRun]` (`88-104`): ordered by `started_at DESC`.
- `get_run(run_id: str) -> Optional[WorkflowRun]` (`105-110`).
- `create_run(project_id, workflow_id, input_data?) -> WorkflowRun` (`112-149`): inserts pending run with `input_json`; sets `last_message`.
- `update_run_status(run_id, status, last_message?, finished?, output_data?) -> Optional[WorkflowRun]` (`151-199`): updates columns, optionally sets `finished_at` when `finished` truthy, emits `workflow.run.updated`.
- `get_node_state(run_id, node_id)`, `set_node_state(...) -> WorkflowNodeState` (`201-297`): upsert node state, update timestamps when `started/completed` flags passed, emit `workflow.node_state.updated`.
- `list_node_states(run_id) -> List[WorkflowNodeState]` (`298-301`).
- `execute_workflow_run(run_id)` async (`303-404`): loads run/graph, updates status to running, emits start event, compiles graph, streams LangGraph events to `_handle_execution_event`, invokes graph to completion, updates/ emits final state; handles cancel and exceptions.
- `_handle_execution_event(run_id, project_id, event)` async (`405-452`): reacts to LangGraph `on_chain_start/end/error` by setting node states and emitting node events.
- `cancel_workflow_run(run_id)` async (`453-503`): validates status, marks run cancelled/finished, marks running node states cancelled, emits cancelled.
- `pause_workflow_run(run_id, checkpoint_data?)` async (`504-542`): requires RUNNING, stores `paused_at` and `checkpoint_json`, emits paused.
- `resume_workflow_run(run_id)` async (`543-583`): requires PAUSED, sets status RUNNING, schedules execution, emits resumed.
- `get_execution_status(run_id) -> dict` (`584-611`): aggregates progress average across node states, current running node, started_at, node state dumps.

**Compiler** (`backend/app/services/workflow_compiler.py`):
- `WorkflowGraphCompiler.compile(workflow_graph)` (`37-63`): builds LangGraph nodes/edges; entry is edge from `__start__` or first node; connects edges to `END` when target `__end__`; returns compiled graph.
- Node function (`64-159`): logs start, optionally sets node state RUNNING; sleeps 0.1s; executes `_execute_node_logic` stub; sets node state COMPLETED with success message; on exceptions sets FAILED and re-raises.
- `_execute_node_logic(node, state)` (`161-200`): stub returning dict with node metadata and processed input; no side effects.

**API endpoints** (`backend/app/api/routes/workflows.py`):
- `GET /api/projects/{project_id}/workflows/graphs` → list graphs (`25-32`).
- `GET /api/projects/{project_id}/workflows/graphs/{workflow_id}` → single graph or 404 (`34-43`).
- `POST /api/projects/{project_id}/workflows/runs` → create run, schedule execution background (`46-65`); 404 if graph missing.
- `GET /api/projects/{project_id}/workflows/runs` → list runs (optional `workflow_id`) (`68-75`).
- `GET /api/projects/{project_id}/workflows/runs/{run_id}` → get run or 404 (`77-84`).
- `POST /api/projects/{project_id}/workflows/runs/{run_id}/execute` → (re)start run, optional input update, scheduled via background task or asyncio (`87-125`); 400 if already running, 409 if completed, 404 if missing.
- `POST /api/projects/{project_id}/workflows/runs/{run_id}/cancel` → cancel run; 400 invalid status, 404 missing (`128-139`).
- `POST /api/projects/{project_id}/workflows/runs/{run_id}/pause` → pause; 400 invalid status, 404 missing (`142-153`).
- `POST /api/projects/{project_id}/workflows/runs/{run_id}/resume` → resume; 400 invalid status, 404 missing (`156-172`).
- `GET /api/projects/{project_id}/workflows/runs/{run_id}/status` → aggregated execution status dict or 404 (`175-184`).

## Data Models
- WorkflowGraph: `{id: str, name: str, description?: str, nodes: [WorkflowNode], edges: [WorkflowEdge]}` (`backend/app/domain/models.py:65-71`).
- WorkflowNode: `{id: str, label: str, x: float, y: float}` (`backend/app/domain/models.py:52-57`).
- WorkflowEdge: `{id: str, source: str, target: str}` (`backend/app/domain/models.py:59-63`).
- WorkflowRun: `{id, workflow_id, status (pending|running|completed|failed|cancelled|paused), started_at, finished_at?, last_message?, task_id?, paused_at?, cancelled_at?}` (`backend/app/domain/models.py:73-92`).
- WorkflowNodeState: `{node_id, status (idle|running|completed|failed|cancelled), progress [0.0-1.0]}`; DB also stores messages_json, started_at/completed_at, error but mapper drops these fields (`backend/app/domain/models.py:94-106`, `backend/app/services/workflow_service.py:236-247,643-647`).
- DB schema mirrors these entities with JSON blobs for graphs, inputs, outputs, checkpoint, messages (`backend/app/db.py:225-271`).

## Control Flows
- **Run creation**: API validates graph exists → `create_run` inserts pending run with input JSON → background task schedules `execute_workflow_run` (`backend/app/api/routes/workflows.py:50-65`).
- **Execution**: `execute_workflow_run` loads run/graph, fetches project_id, sets status RUNNING, emits `workflow.run.created`, compiles graph, streams LangGraph events to `_handle_execution_event` (updates node states on chain start/end/error), then `ainvoke` for final state, updates run to COMPLETED with output, emits completion; handles cancellations and exceptions with status updates and events (`backend/app/services/workflow_service.py:303-404`).
- **Node processing**: LangGraph node function sets node RUNNING, sleeps, executes stub logic, sets COMPLETED with message; errors set FAILED and propagate (`backend/app/services/workflow_compiler.py:64-159`).
- **Cancellation**: validates status, updates run to CANCELLED with timestamps and message, marks RUNNING node states as CANCELLED, emits cancelled (`backend/app/services/workflow_service.py:453-503`).
- **Pause/Resume**: pause stores checkpoint JSON and paused_at, emits paused; resume flips status to RUNNING, re-schedules execution, emits resumed (`backend/app/services/workflow_service.py:504-583`).
- **Status**: `get_execution_status` averages node progress and reports current RUNNING node id plus node state dumps (`backend/app/services/workflow_service.py:584-611`).

## Config & Runtime Parameters
- Execution uses LangGraph default behavior; no explicit timeouts or retries.
- Uses asyncio background tasks; relies on event loop availability from FastAPI.
- No configuration toggles specific to workflows beyond DB connection and global settings from core module (see `backend-core` spec).

## Error & Failure Semantics
- API returns 404 for missing graph/run; 400 for invalid run state on cancel/pause/resume; 409 for execute on completed run (`backend/app/api/routes/workflows.py:99-140,150-172`).
- `update_run_status` only sets `finished_at` when `finished` truthy; callers must pass flag (done on completion/cancel paths) (`backend/app/services/workflow_service.py:151-199`).
- Node state mapper discards error/messages/timestamps; downstream consumers may miss diagnostics (`backend/app/services/workflow_service.py:636-647`).
- Event emission is fire-and-forget via `asyncio.create_task`; failures are logged but not surfaced to API (`backend/app/services/workflow_service.py:189-197,288-294,328-378,385-403`).
- `_handle_execution_event` assumes LangGraph emits `on_chain_*`; if absent, node states may remain idle despite execution (`backend/app/services/workflow_service.py:405-452`).
- No transaction bundling across run/node updates; partial updates possible on failure.

## Observability
- Logging via `logging.getLogger("cortex.workflow")` but minimal message content; no structured tracing or metrics (`backend/app/services/workflow_service.py:23`, `backend/app/services/workflow_compiler.py:11`).
- Events propagated to WebSocket clients via streaming service; event payloads include `run` or `nodeState` plus timestamp (`backend/app/services/streaming_service.py:112-124`).
- No health endpoints or per-run telemetry beyond node states and final output JSON.

## Risks, Gaps, and [ASSUMPTION] Blocks
- No API to create/update workflow graphs; persistence method unused externally. [ASSUMPTION] Graphs are pre-seeded or manually inserted; otherwise list endpoints return empty and runs cannot be created.
- Execution logic is stubbed (sleep + echo output); no branching/tooling/LLM integration yet. Downstream consumers may expect real workflows. [ASSUMPTION] Future expansion will implement node types/config.
- Node state mapping omits messages/error/timestamps, losing diagnostics; DB columns are unused in responses.
- `_handle_execution_event` duplicates state updates performed inside compiler’s node functions, potentially racing or double-emitting events.
- `update_run_status` skips `finished_at` unless `finished=True`; some status changes may lack completion timestamps.
- No concurrency limits or queueing; simultaneous background tasks may overload SQLite (`check_same_thread=False` but no locking/backoff).
- Checkpoint/resume ignores stored `checkpoint_json` in execution; resume simply re-executes from scratch.
- No validation that run belongs to project_id in many service methods; APIs supply project_id but service-level updates don’t enforce project scoping.

## Verification Ideas
- Add API test to assert 404 on run creation with nonexistent workflow_id; seed a sample graph and verify create/list/get flows and persisted `graph_json`.
- Integration test for execution: create graph with two nodes connected via `__start__` and `__end__`, create run, trigger execute, poll status until completed, assert node states marked completed with progress 1.0.
- Test cancel/pause/resume state transitions: create run, start execution, call cancel/pause/resume, assert DB columns (`paused_at`, `cancelled_at`, `finished_at`) set and events broadcast (can inject test connection manager).
- Validate `get_execution_status` progress averaging and running node detection using inserted node states with varying progress.
- Add unit test for compiler edge handling (`__start__`/`__end__`) and default entry fallback; verify node state updates are invoked and errors propagate.

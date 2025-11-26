## Overview
- Roadmap graph management with nodes/edges persisted in SQLite, including dependency validation and cycle checks (`backend/app/services/roadmap_service.py:24-548`).
- LLM-assisted roadmap generation from natural language intent (`backend/app/services/roadmap_service.py:415-548`).

## Responsibilities & Non-Responsibilities
- Responsibilities: CRUD for roadmap nodes/edges; validate dependencies and prevent cycles; filter/paginate nodes/edges; generate roadmap nodes from intent via LLM.
- Non-Responsibilities: lane management beyond filtering, cascade deletes to related entities, advanced scheduling, rich status/priority workflows, observability, migrations.

## Dependencies & Integration Points
- DB tables: `roadmap_nodes`, `roadmap_edges` (`backend/app/db.py:273-308`).
- Domain models: `RoadmapNode/Status/Priority`, `RoadmapEdge/Kind`, `RoadmapGraph` (`backend/app/domain/models.py:327-377`).
- LLM text generation via `generate_text` from `llm_service` for intent-based node creation (`backend/app/services/roadmap_service.py:19,415-548`).
- Ties to ideas/tickets/mission control via optional IDs on nodes.

## Interfaces & Contracts
- Nodes: `list_nodes(project_id, cursor?, limit?, status?, lane_id?) -> PaginatedResponse` (`30-74`); `get_node` (`75-82`); `create_node(project_id, node_data)` (`84-143`); `update_node(project_id, node_id, updates)` (`145-197`); `delete_node(project_id, node_id)` checks dependents and removes edges (`198-215`).
- Edges: `list_edges(project_id, cursor?, limit?) -> PaginatedResponse` (`217-241`); `create_edge` validates nodes, dupes, and cycles (`242-299`); `delete_edge` (`301-305`).
- Graph: `get_graph(project_id)` loads up to 1000 nodes/edges (`306-314`).
- Intent generation: `create_roadmap_nodes_from_intent(project_id, intent)` prompts LLM for JSON array of nodes, creates nodes, then updates dependencies by label mapping (`415-535`).

## Data Models
- `RoadmapNode {id, project_id, label, description?, status pending|active|complete|blocked, priority?, start_date?, target_date?, depends_on_ids[], lane_id?, idea_id?, ticket_id?, mission_control_task_id?, created_at, updated_at}`.
- `RoadmapEdge {id, project_id, from_node_id, to_node_id, kind depends_on|relates_to, label?, created_at}`.
- Graph capped at 1000 items per list call.

## Control Flows
- Node creation: validate dependencies exist; normalize status/priority strings; insert row with depends_on_ids_json; timestamps set to now.
- Node update: validate existence; optional dependency validation and cycle detection; update allowed fields; refresh updated_at.
- Node delete: block if other nodes depend on it; delete connecting edges; delete node.
- Edge creation: validate nodes, check duplicate, check for cycles via DFS, insert edge.
- Graph fetch: list nodes/edges with limit 1000 each; return `RoadmapGraph`.
- Intent-based creation: call LLM to generate JSON; create nodes (first pass), then resolve dependencies by label and update nodes (second pass); logs success; raises on JSON parse/errors.

## Config & Runtime Parameters
- No configurable limits aside from hardcoded list limit + 1000 cap; status/priority normalized to enums with fallbacks.
- LLM prompt uses temperature 0.3, max_tokens=2000, json_mode=True; model via `llm_service.generate_text` defaults.

## Error & Failure Semantics
- ValueError for missing nodes on updates/deletes, invalid dependencies, duplicate edges, or cycles; callers should translate to HTTP errors.
- LLM generation errors or parse failures raise ValueError with context.
- No transaction bundling across edge/node sequences; partial updates possible on failure.

## Observability
- Logging via `logger` for create intent start/success/errors; other CRUD paths largely silent; no metrics/traces.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Graph size capped silently at 1000 nodes/edges; larger graphs truncated.
- No API router shown here—ensure routes wrap ValueErrors appropriately.
- No cascade cleanup for related idea/ticket/task references; orphans possible.
- LLM-generated nodes use two-pass label mapping; dependency labels must match exactly; no duplicate-label handling.
- Cycle detection uses DB queries per DFS; performance may degrade on large graphs.

## Verification Ideas
- Service/API tests: create/update/delete nodes with dependencies; ensure cycles rejected; delete blocked when dependents exist; edge duplicate check.
- Intent generation tests with mocked LLM to produce JSON; verify nodes created, dependencies resolved; error handling on invalid JSON.
- Pagination tests for list_nodes/edges; confirm next_cursor behavior and status/lane filters.

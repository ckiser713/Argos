## Overview
- Ideas service handling idea candidates, clusters, tickets, and mission-control tasks stored in SQLite (`backend/app/services/idea_service.py:25-509`).
- Project intelligence helper for heuristic extraction and gap analysis support types (`backend/app/services/project_intel_service.py:1-239`).

## Responsibilities & Non-Responsibilities
- Responsibilities: CRUD-ish operations for candidates/clusters/tickets/tasks; basic filtering/pagination; mission-control task mapping onto tickets; heuristic extraction utilities for idea candidates (project intel).
- Non-Responsibilities: rich validation, referential integrity between ideas/roadmaps/ingest, persistence of embeddings/labels beyond stubs, concurrency control, cascade deletes, sophisticated scoring or planner integration (optional clients).

## Dependencies & Integration Points
- DB tables: `idea_candidates`, `idea_clusters`, `idea_tickets` (`backend/app/db.py:128-143,145-156,89-103`).
- Domain models: IdeaCandidate/Status, IdeaCluster, IdeaTicket/Status/Priority, MissionControlTask/Column/Origin, ContextItem/Type (`backend/app/domain/models.py:235-321`).
- Project intel service uses optional `planner_client` and `embedding_client` if present; otherwise falls back to heuristics (`backend/app/services/project_intel_service.py:23-87,152-236`).
- Gap analysis consumes tickets via `project_intel_repo` (see gap-analysis module).

## Interfaces & Contracts
**Idea service** (`backend/app/services/idea_service.py`):
- Candidates: `list_candidates(project_id, cursor?, limit?, status?, type?) -> PaginatedResponse` (`30-66`); `create_candidate(project_id, candidate_data)` (`67-106`); `update_candidate(project_id, candidate_id, updates)` (`108-136`).
- Clusters: `list_clusters(project_id, cursor?, limit?)` (`137-161`); `create_cluster(project_id, cluster_data)` (`162-197`).
- Tickets: `list_tickets(project_id, cursor?, limit?, status?)` (`199-231`); `create_ticket(project_id, ticket_data)` inserts into `idea_tickets`, sets cluster_id=idea_id (`232-279`).
- Tasks (mission control): `list_tasks(project_id, cursor?, limit?, column?, origin?)` maps tickets to tasks; `create_task(project_id, task_data)` stores as ticket with JSON description encoding origin/confidence/column; `update_task` updates title/status/priority (`280-425`).
- Internal mappers `_row_to_candidate/_row_to_cluster/_row_to_ticket/_ticket_row_to_task` populate domain models, sometimes with defaults (e.g., candidate status always "active", confidence 0.85) (`427-508`).

**Project intel service** (`backend/app/services/project_intel_service.py`):
- Heuristic extraction from chat segments: `extract_idea_candidates_from_segments` uses keyword rules to build IdeaCandidate models with stable IDs; optional planner refinement (`152-236`).
- Helpers for embeddings and cosine similarity (not wired into services here); optional planner/embedding clients gracefully absent.

## Data Models
- IdeaCandidate DB schema stores source ids/text; service returns `IdeaCandidate` with defaulted type/status/confidence and ignores many DB columns.
- IdeaCluster stored with `name`/`summary` and `idea_ids_json`; service maps to `IdeaCluster` label/description/idea_ids.
- IdeaTicket stored with cluster_id, status/priority, origin_idea_ids_json; service maps to domain with limited fields.
- MissionControlTask is derived view over tickets with JSON-encoded description storing origin/column/confidence.
  - Columns lifecycle: `backlog` → `todo` → `in_progress` → `done`; transitions are unconstrained in code but should follow this order.
  - IdeaTicketStatus lifecycle: `active` → `blocked`|`complete`; no other values used in code.

## Control Flows
- Candidate creation: generate UUID, build candidate, insert into DB with summary in both original_text/summary, default source IDs, no embeddings.
- Cluster creation: build cluster, insert with idea_ids_json from input.
- Ticket creation: insert with cluster_id from idea_id, origin_idea_ids_json from idea_id list, default status/priority if absent.
- Task creation: build MissionControlTask, store as ticket with description JSON capturing origin/confidence/column; later read via `_ticket_row_to_task`.
- List endpoints: filter by project and optional status/type; pagination via limit+1 with next_cursor=id.
- Update candidate/ticket/task: only limited fields updatable; ValueError on missing.

## Config & Runtime Parameters
- No tunable settings; defaults baked into services (confidence 0.85, status defaults, etc.).
- Heuristic rules in project_intel are static dicts.

## Error & Failure Semantics
- Missing entity on update raises ValueError (callers must translate to HTTP errors).
- No validation of relationships (idea_id/cluster_id existence); may create inconsistent data.
- Candidate mapper ignores DB status/confidence and hardcodes values; information loss.
- Task status mapping uses column→status map; origin filter not applied in list_tasks.

## Observability
- Minimal logging (project_intel uses logger; idea service silent).

## Risks, Gaps, and [ASSUMPTION] Blocks
- Misalignment between DB schema and returned models (e.g., candidate status/confidence ignored; tickets’ origin_idea_ids unused). [ASSUMPTION] Acceptable for current UI, but risks data loss.
- No delete operations for candidates/clusters/tickets; accumulation unbounded.
- No referential integrity checks (cluster_id/idea_id may not exist); mission-control tasks stored as tickets with JSON blobs may confuse other consumers.
- Planner/embedding clients optional; extraction quality depends on heuristics.
- No auth/ownership checks beyond project_id filtering.

## Verification Ideas
- API/service tests: create/list/update candidates/clusters/tickets/tasks; ensure project scoping and pagination; validate mission-control column→status mapping.
- Consistency tests: ensure cluster_id/idea_id references existing records; add delete endpoints and tests if needed.
- Project intel tests: heuristic extraction from sample chat segments; planner/embedding error handling; stable ID generation determinism.

## Overview
- Context item management with a simple token budget per project stored in SQLite (`backend/app/services/context_service.py:17-162`, `backend/app/api/routes/context.py:17-73`).
- Supports listing items, computing budget, adding items with budget enforcement, updating pin/tokens, and removing items.

## Responsibilities & Non-Responsibilities
- Responsibilities: persist context items per project; enforce a fixed token budget on additions; expose CRUD-ish endpoints for items and budget retrieval.
- Non-Responsibilities: configurable budgets, item type-specific handling, eviction policies, transactional coordination with ingest/knowledge, concurrency controls, observability.

## Dependencies & Integration Points
- DB table: `context_items` (`backend/app/db.py:168-180`).
- Domain models: `ContextItemType`, `ContextItem`, `ContextBudget`, `AddContextItemsRequest/Response` (`backend/app/domain/models.py:15-47`).
- HTTP router exposes project-scoped endpoints; no auth beyond global dependency.

## Interfaces & Contracts
**API endpoints** (`backend/app/api/routes/context.py`):
- `GET /api/projects/{project_id}/context` → `ContextBudget` (items included) (`17-20`).
- `POST /api/projects/{project_id}/context/items` → `AddContextItemsResponse`; body list of `ContextItem` with tokens/pinned/type enforced; 400 on budget exceed (`22-33`).
- `PATCH /api/projects/{project_id}/context/items/{context_item_id}` → `ContextItem`; body is arbitrary dict; extracts `pinned`/`tokens` only; 404 if not found (`35-53`).
- `DELETE /api/projects/{project_id}/context/items/{context_item_id}` → `ContextBudget` after removal; 404 if not found (`56-68`).
- `GET /api/projects/{project_id}/context/items` → List of `ContextItem` for project (`71-73`).

**Service methods** (`backend/app/services/context_service.py`):
- `list_items(project_id?)` → all items, optionally filtered by project (`24-33`).
- `get_budget(project_id)` → sum tokens over items; uses `DEFAULT_MAX_TOKENS=100000` as total (`34-46`).
- `add_items(project_id, AddContextItemsRequest)` → checks budget, inserts items with generated UUIDs, returns created items and updated budget; raises ValueError on budget exceed (`48-98`).
- `update_item(project_id, item_id, pinned?, tokens?)` → validates ownership, updates fields, returns updated item; ValueError on missing (`99-135`).
- `remove_item(project_id, item_id)` → deletes item, returns updated budget; ValueError on missing (`136-149`).

## Data Models
- `ContextItem {id, name, type pdf|repo|chat|other, tokens>=0, pinned bool, canonical_document_id?, created_at?}`.
- `ContextBudget {project_id, total_tokens, used_tokens, available_tokens, items[]}` with default total 100000 (hardcoded).
- `AddContextItemsRequest {items: [ContextItem]}`, `AddContextItemsResponse {items[], budget}`.

## Control Flows
- Budget: calculated on every add via `get_budget`; reject additions exceeding `DEFAULT_MAX_TOKENS`; no persistence of budget separately.
- Adds: insert each item row with pinned flag as int; created_at set to now; return new budget snapshot.
- Updates: allow pinned/tokens changes; no validation of token budget on updates.
- Deletes: remove item; recompute budget afterward.

## Config & Runtime Parameters
- `DEFAULT_MAX_TOKENS=100000` hardcoded; not configurable per environment/project.
- No pagination; lists return all items for project.

## Error & Failure Semantics
- Budget exceed → ValueError → 400 response.
- Missing item on update/delete → ValueError → 404.
- No validation of item `name`/`type` beyond enum enforcement; updates ignore unknown fields silently.
- No transaction bundling for multi-item add beyond single commit; partial failure not explicitly handled.

## Observability
- No logging/metrics; budget decisions and errors are silent except for HTTP responses.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Fixed budget not configurable; [ASSUMPTION] 100k tokens suits all projects.
- Updates do not re-check budget; increasing tokens could exceed limit silently.
- No deduplication or canonical doc linkage validation; context items may reference nonexistent docs.
- Unbounded list endpoints could grow large without pagination.
- No pinning semantics beyond boolean; no LRU/eviction or ordering.

## Verification Ideas
- Tests: add items within budget succeeds; exceeding budget returns 400; update pinned/tokens reflects in DB; delete removes item and updates budget.
- Edge: update tokens to exceed budget should be defined (decide to reject or allow); add items with mixed types.
- Performance: add pagination to list endpoints; add config-driven budget and test overrides.

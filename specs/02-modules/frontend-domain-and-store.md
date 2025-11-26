## Overview
- Frontend domain types and API mapping under `frontend/src/domain/` plus global store in `frontend/src/state/cortexStore.ts`.
- Provides types for backend entities (projects, ingest jobs, context items, knowledge graph, ideas/tickets/roadmap) and API response shapes.

## Responsibilities & Non-Responsibilities
- Responsibilities: define TypeScript types/interfaces for API data; expose Zustand store for shared state (projects, context items, ingest jobs, ideas, knowledge graph).
- Non-Responsibilities: actual API fetching (handled by hooks/lib), validation, error handling, persistence.

## Dependencies & Integration Points
- Hooks in `frontend/src/hooks/*` consume these types and store slices.
- `cortexApi` client uses `ApiResponse<T>` types (see frontend-hooks/components specs).
- Store uses Zustand; components/hooks should import selectors.

## Key Types (selected)
- `api-types.ts`: defines REST request/response shapes, e.g., `Project`, `ContextItem`, `IngestJob`, `Idea`, `RoadmapNode`, `RoadmapEdge`, `KnowledgeNode/Edge`, `AgentRun`, `WorkflowRun`, `MissionControlTask`, `Paginated<T>`, etc.
- `types.ts`: UI-focused types for force graph, roadmap, missions, etc.; includes node/edge shapes, color schemes, roadmap lanes, mission board columns.

## Store (`frontend/src/state/cortexStore.ts`)
- Zustand store with slices: projects, context, ingest, ideas, knowledgeGraph, missionControl; actions to set/add/update entities; loading/error flags.
- State fields align with domain types (project list, context items, ingest jobs, ideas, knowledgeGraph nodes/edges, missionControl tasks).

## Control Flows
- Store actions are synchronous setters; no side effects or persistence.
- Types define expected shapes for hooks to map API data into UI components.

## Config & Runtime Parameters
- None; pure typing/state.

## Error & Failure Semantics
- Store does not track errors except `ingestError` string; no retries or status lifecycles.

## Observability
- None.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Types may diverge from backend contracts (ensure alignment with specs/backend); [ASSUMPTION] maintain consistency when backend changes.
- Store lacks per-entity loading/error granularity; large updates overwrite state wholesale.
- No persistence or versioning; refresh resets state.

## Verification Ideas
- Type-level checks against OpenAPI/backend models; add unit tests to ensure store actions update state as expected.
- Integration tests mapping API responses through hooks into store updates.

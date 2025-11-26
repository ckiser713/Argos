## Overview
- React hooks in `frontend/src/hooks/` for projects, context, ingest, ideas, roadmap, knowledge graph, agent runs, and toast handling.
- Core UI components: `ErrorBoundary`, `ErrorDisplay`, `ToastContainer`, plus tests/utilities.
- HTTP client wrappers in `frontend/src/lib/` for API calls and error handling.

## Responsibilities & Non-Responsibilities
- Responsibilities: fetch/update backend resources via `cortexApi`/`http` helpers; manage local loading/error state; provide UI error/toast surface.
- Non-Responsibilities: global caching (beyond hook state), auth, input validation, complex state management (handled via Zustand store separately).

## Dependencies & Integration Points
- `cortexApi.ts` encapsulates fetch calls to `/api/*`; `http.ts` wraps fetch with JSON handling; `errorHandling.ts` formats errors.
- Hooks interact with store `cortexStore` to set entity lists.
- Components consume hooks/store to display errors/toasts; tests under `frontend/src/components/__tests__` and `frontend/src/hooks/__tests__`.

## Interfaces & Contracts (hooks)
- `useProjects` fetches `/api/projects` into store; returns loading/error.
- `useContextItems` fetches `/api/projects/{projectId}/context/items`; supports add/remove; uses store.
- `useIngestJobs` fetches `/api/projects/{projectId}/ingest/jobs`; supports create via upload/source path, cancel, delete; updates store.
- `useIdeas` covers ideas/tickets/tasks; fetches lists and mutators aligned to backend endpoints (may have gaps if backend differs).
- `useRoadmap` fetches roadmap nodes/edges; supports add/update/delete; uses backend roadmap routes.
- `useKnowledgeGraph` fetches nodes/edges/search; integrates with Qdrant-backed endpoints.
- `useAgentRuns` fetches/streams agent runs and related data.
- `useToast` manages toast notifications; `useToast` consumed by UI components.

## Interfaces & Contracts (components)
- `ErrorBoundary.tsx`: React error boundary wrapper.
- `ErrorDisplay.tsx`: renders error messages in a styled card.
- `ToastContainer.tsx`: renders toasts from `useToast`.

## Tests/Utils
- `frontend/src/components/__tests__` and `frontend/src/hooks/__tests__` (not fully listed here) provide component and hook tests.
- `frontend/src/test/testUtils.tsx` offers rendering utilities with providers.

## Config & Runtime Parameters
- API base path assumed `/api`; no env-based switching evident.
- Hooks may assume certain field names (camelCase) that must align with backend.

## Error & Failure Semantics
- Hooks likely set local error state and may throw to ErrorBoundary; Toasts used for user feedback.
- `http.ts` likely throws on non-2xx; `errorHandling.ts` shapes errors.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Potential contract drift with backend (e.g., agent_id/project_id requirements, ingest routes); [ASSUMPTION] hooks match backend but needs verification.
- Missing auth handling; all calls unauthenticated.
- No retry/backoff; minimal pagination support.
- Tests may be incomplete (some TODOs noted in docs/specs).

## Verification Ideas
- Align hook request/response shapes with backend specs; add integration tests using mocked fetch.
- Component tests for ErrorBoundary/Toast behavior; hook tests for error handling and store updates.
- Ensure roadmap/ideas/ingest hooks handle 404/400 error semantics as per backend.

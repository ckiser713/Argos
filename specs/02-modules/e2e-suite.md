## Overview
- Playwright end-to-end suite under `e2e/` with multiple specs: ingestion, knowledge, projects, agents, context, performance, accessibility, websocket, visual regression, UI components, and edge cases.
- Uses shared fixtures (`e2e/fixtures.ts`, `e2e/utils`) and UI-focused tests under `e2e/ui/`.

## Responsibilities & Non-Responsibilities
- Responsibilities: validate end-to-end flows across frontend/backend, including real-time features and UI behaviors; provide coverage roadmap (see README/roadmap specs).
- Non-Responsibilities: unit testing, backend-only integration tests, performance/load beyond basic checks; comprehensive WebSocket client (not fully implemented).

## Structure
- Top-level specs: `accessibility.spec.ts`, `agent-runs.spec.ts`, `context.spec.ts`, `cross-browser.spec.ts`, `edge-cases.spec.ts`, `example.spec.ts`, `ingest.spec.ts`, `knowledge.spec.ts`, `performance.spec.ts`, `projects.spec.ts`, `roadmap.spec.ts`, `visual-regression.spec.ts`, `websocket.spec.ts`, `websocket-full.spec.ts`.
- UI folder: `e2e/ui/components.spec.ts`, `components-detailed.spec.ts`.
- Config: `e2e/tsconfig.json`, Playwright config `playwright.config.ts`.

## Known Gaps/TODOs
- TODO markers for WebSocket tests (“add more comprehensive WebSocket tests when WebSocket client is implemented”) (`e2e/websocket.spec.ts:54`).
- UI components spec has TODO to add more cases (`e2e/ui/components.spec.ts:36`).
- E2E_TESTING_COMPREHENSIVE.md lists multiple TODOs (WebSocket client, event subscription/filtering/reconnect; component-specific tests; form/error/loading/responsive states).

## Verification Ideas
- Implement missing WebSocket client tests and subscription/filter/reconnect scenarios.
- Expand UI component specs for new components and state variations.
- Align E2E flows with backend contract (agent runs, ingest jobs, workflows) as backend matures.

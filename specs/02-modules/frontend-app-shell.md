## Overview
- Frontend app shell in `frontend/App.tsx` orchestrates a highly-stylized UI with animated panels and multiple feature modules: Mission Control board, Dependency Timeline, Roadmap map, Knowledge Nexus, Ingest Station, Deep Research, Workflow Construct, Strategy Deck, PM Dissection, etc.
- Uses Framer Motion for animated tab transitions, React state for mock data/logs/system status, and custom components from `frontend/components`.

## Responsibilities & Non-Responsibilities
- Responsibilities: render main layout, manage active tab, simulate system logs/VRAM usage/workflow node activity, provide mock context items, and compose feature modules.
- Non-Responsibilities: real data fetching, auth/routing, error handling beyond component boundaries, responsive behavior beyond provided CSS, production-ready state management.

## Dependencies & Integration Points
- Components: `Layout`, `GlassCard`, `NeonButton`, `TerminalText`, `ScrambleText`, `KnowledgeNexus`, `IngestStation`, `DeepResearch`, `WorkflowConstruct`, `MissionControlBoard`, `DependencyTimeline`, `StrategyDeck`, `PmDissection`, `DecisionFlowMap`, `SoundManager`, `ContextPrism` (imported from `frontend/components`, not fully inspected here).
- Icons: `lucide-react` Activity/Shield/Cpu/Terminal/Wifi/Database.
- React Flow types `Node`/`Edge` for mock workflow graph.
- Framer Motion for animations.

## Interfaces & Contracts
- App maintains internal state: `systemStatus`, `activeTab`, `vram`, `logs`, `wfActiveNode`, `wfVisited`, `contextItems`.
- Simulates workflow step progression when `activeTab === 'workflow'` with hardcoded node sequence and timers.
- Provides `usedTokens` derived from mock context items to the `Layout` header (assumed via props).
- Tab rendering switch cases: mission_control→`<MissionControlBoard/>`; timeline→`<DependencyTimeline/>`; roadmap→`<DecisionFlowMap/>`; strategy→`<StrategyDeck/>`; ingest→`<IngestStation/>`; research→`<DeepResearch/>`; knowledge→`<KnowledgeNexus/>`; workflow→`<WorkflowConstruct .../>`; pm_dissection→`<PmDissection/>`.
- Context ejection handler removes items and appends log entry.

## Data Models
- Mock `ContextItem` type from `ContextPrism` used for context list: `{id,name,type,tokens}`.
- Mock workflow graph nodes/edges arrays for `WorkflowConstruct`.

## Control Flows
- useEffect to simulate logs/VRAM drift every 2.5s.
- useEffect adjusts VRAM when systemStatus toggles.
- useEffect drives workflow node activation loop when workflow tab active.
- `handleEjectContext` filters context items and appends log.
- `renderContent` switch selects tab content, each wrapped in Framer Motion for transition.

## Config & Runtime Parameters
- No runtime config; all mock data hardcoded.

## Error & Failure Semantics
- No error boundaries around child components in App shell; `ErrorBoundary` component exists but not used here.

## Observability
- Not applicable; mock logging shown in UI only.

## Risks, Gaps, and [ASSUMPTION] Blocks
- Mock-only implementation; not wired to backend APIs or state store; [ASSUMPTION] intended as demo.
- Tab list/features not aligned with actual backend endpoints; ensure when integrating real data.
- Workflow simulation uses hardcoded sequence; not reflective of real workflow runs.

## Verification Ideas
- Component-level tests to ensure tab switching renders appropriate components and workflow simulation runs/clears timers.
- Integration plan to replace mock data with hooks/API calls; add error boundaries around feature components.

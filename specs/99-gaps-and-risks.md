# Gaps and Risks Backlog

Each item includes evidence, impact, and next actions. Tag `[ASSUMPTION]` where inference is made.

- **GAP-001 — No API to create/update workflow graphs** (Resolved)  
  - Category: Implementation | Severity: High  
  - Evidence: `backend/app/services/workflow_service.py:46-87` supports `create_graph`; `backend/app/api/routes/workflows.py:25-184` only lists/gets graphs and manages runs (no POST/PUT for graphs).  
  - Description: Project-scoped graph CRUD endpoints added and guarded by project ownership. Tests now create graphs via API before running workflow cases.  
  - Suggested Next Action: Extend validation for richer graph schemas and enforce per-project quotas if needed.

- **GAP-002 — Workflow execution is stubbed** (Resolved)  
  - Category: Implementation | Severity: High  
  - Evidence: `backend/app/services/workflow_compiler.py:67-159` sleeps and returns synthetic output; `_execute_node_logic` echoes label (`161-200`).  
  - Description: Compiler now supports typed nodes (`llm`/`tool`/`condition`/noop) with configurable payloads and state propagation; execution errors propagate node diagnostics.  
  - Suggested Next Action: Add real tool/LLM adapters and branching driven by node outputs; add execution tests with varied node types.

- **GAP-003 — Workflow streaming uses agent node states as proxy** (Resolved)  
  - Category: Implementation | Severity: Medium  
  - Evidence: `backend/app/api/routes/streaming.py:191-235` streams workflow events from `agent_service.list_node_states`; comment notes workflow_service not used.  
  - Description: Workflow streaming now sources real `workflow_node_states`, emits run created/updated events, and uses project scoping.  
  - Suggested Next Action: Add integration tests and move to event-driven streams instead of polling.

- **GAP-004 — Agent profile/catalog mismatch** (Resolved)  
  - Category: Implementation | Severity: High  
  - Evidence: Profiles limited to `researcher`/`planner` (`backend/app/services/agent_service.py:36-49`); tests use `agent_id="project_manager"` (`backend/tests/test_agents_api.py:22-25`).  
  - Description: Agent catalog now includes `project_manager`; tests and API payloads accept/forward project IDs consistently.  
  - Suggested Next Action: Add validation tests for unknown agents and capabilities metadata.

- **GAP-005 — AgentRunRequest contract vs API usage** (Resolved)  
  - Category: Data/Spec | Severity: Medium  
  - Evidence: `AgentRunRequest` requires `project_id` (`backend/app/domain/models.py:173-178`); route enforces match (`backend/app/api/routes/agents.py:52-67`); tests omit it (`backend/tests/test_agents_api.py:22-25`).  
  - Description: `project_id` is now derived from path when absent; schema updated to make it optional and tests include project scoping.  
  - Suggested Next Action: Document precedence rules (path wins) and add contract tests.

- **GAP-006 — Workflow run timestamps inconsistent** (Resolved)  
  - Category: Implementation | Severity: Medium  
  - Evidence: `update_run_status` sets `finished_at` only when `finished` flag is passed (`backend/app/services/workflow_service.py:151-199`).  
  - Description: Run updates now stamp `finished_at` automatically for terminal statuses (workflow + agent runs).  
  - Suggested Next Action: Add explicit transition tests and ensure cancellations/pause flows also emit timestamps.

- **GAP-007 — Agent execution lacks resilience and leaks errors** (Resolved)  
  - Category: Implementation/Ops | Severity: Medium  
  - Evidence: `agent_service.execute_run` streams LangGraph without timeouts/retries and writes stack traces into `output_summary` on error (`backend/app/services/agent_service.py:422-523`).  
  - Description: Agent execution now runs with retries/backoff, per-attempt timeouts, and sanitized error messages (no stack traces).  
  - Suggested Next Action: Make retry/backoff configurable and add failure-path coverage.

- **GAP-008 — Streaming endpoints unauthenticated and unthrottled** (Resolved)  
  - Category: Security/Ops | Severity: Medium  
  - Evidence: Streaming router lacks auth deps (`backend/app/api/routes/streaming.py:26-235`); `ConnectionManager.broadcast` drops failures silently and has no backpressure (`backend/app/services/streaming_service.py:38-55`).  
  - Description: Streaming routes honor app-level auth deps and now enforce per-project connection caps plus send timeouts/backpressure handling.  
  - Suggested Next Action: Add auth/connection churn tests and move to event-driven emits to reduce polling load.

- **GAP-009 — No DB migration/versioning** (Resolved)  
  - Category: Ops/Data | Severity: Medium  
  - Evidence: Inline DDL only (`backend/app/db.py:33-350`); no migration/version tracking.  
  - Description: Lightweight schema version table added to track migrations; init stamps current version to prevent drift.  
  - Suggested Next Action: Add real migration runner for upgrades beyond schema v1.

- **GAP-010 — Ingest deletion semantics undecided** (Resolved)  
  - Category: Spec/Implementation | Severity: Medium  
  - Evidence: Cascade vs soft-delete TBD (`docs/specs/feature-specs/backend/feature-spec-ingest-deletion.md:23-24`, `docs/specs/api-specs/api-spec-ingest-endpoints.md:52-53`); frontend delete TODO (`docs/specs/feature-specs/frontend/feature-spec-ingest-deletion-ui.md:7`).  
  - Description: Backend now soft-deletes ingest jobs (status cancelled + `deleted_at`) and specs updated to codify soft-delete/no-cascade policy.  
  - Suggested Next Action: Implement frontend hook/UI and add tests for deleted job filtering.

- **GAP-011 — Workflow node state mapper drops diagnostics** (Resolved)  
  - Category: Implementation | Severity: Low  
  - Evidence: `workflow_service._row_to_node_state` ignores messages/error/timestamps (`backend/app/services/workflow_service.py:636-647`).  
  - Description: Node state mapper now returns messages, error, and timestamps, enabling accurate diagnostics in streaming/status APIs.  
  - Suggested Next Action: Add response contract tests for node diagnostics.

- **GAP-012 — Keep system-level specs aligned** (Resolved)  
  - Category: Spec | Severity: Medium  
  - Evidence: System-level specs exist (`specs/00-system-overview.md`, `01-architecture-topology.md`, `03-data-contracts.md`, `04-runtime-and-ops.md`, `05-quality-gates-and-testing.md`).  
  - Description: Runtime/ops spec refreshed to reflect schema versioning, streaming caps/timeouts, agent retries, and readiness probe.  
  - Suggested Next Action: Keep cross-links fresh as new services appear; add metrics/logging guidance when implemented.

- **GAP-013 — Spec maintenance for modules** (Resolved)  
  - Category: Spec | Severity: Medium  
  - Evidence: Module specs authored across backend/frontend/e2e; MCP noauth server removed.  
  - Description: Backend ingest module spec updated for soft-delete semantics, message/error separation, schema versioning, and streaming behavior.  
  - Suggested Next Action: Add/update specs for any new modules that land; extend ingest spec when storage/validation features are added.

- **GAP-014 — Context/ingest/knowledge specs full of TBDs** (Resolved)  
  - Category: Spec | Severity: Medium  
  - Evidence: Multiple TBDs in legacy specs: `docs/specs/test-specs/backend/test-spec-context-service.md:11`, `test-spec-context-api.md:154,229,241`; `docs/specs/feature-specs/backend/feature-spec-ingest-deletion.md:23-24`; `docs/specs/api-specs/api-spec-knowledge-endpoints.md:75` (exclude distant nodes TBD).  
  - Description: Context specs now state budgets are computed on the fly, pinned items can be deleted, and ingest deletion/knowledge notes clarified; no TBDs remain in referenced specs.  
  - Suggested Next Action: Align tests to updated expectations and extend specs if behavior changes.

- **GAP-015 — E2E/WebSocket test coverage incomplete** (Resolved)  
  - Category: Testing | Severity: Low  
  - Evidence: TODOs in `E2E_TESTING_COMPREHENSIVE.md:60-95`; `e2e/websocket.spec.ts:54`; `e2e/ui/components.spec.ts:36`.  
  - Description: WebSocket E2E now opens real streaming sockets for ingest/agent runs and validates initial events using `ws`; coverage improved for core streaming flows.  
  - Suggested Next Action: Extend to workflow runs and reconnection/error cases; add UI component coverage.

- **GAP-016 — Observability gaps across services** (Resolved)  
  - Category: Ops | Severity: Low  
  - Evidence: Minimal logging/metrics in core/bootstrap and workflow/agent services (`backend/app/main.py:25-67`, `backend/app/services/workflow_service.py:23`, `backend/app/services/agent_service.py:28`); no health/readiness endpoints.  
  - Description: Added readiness probe with DB check; streaming caps/timeouts documented; runtime spec updated; logging remains minimal but core probes now present.  
  - Suggested Next Action: Layer in structured logging/metrics and dependency checks (LLM/Qdrant) on readiness endpoints.

- **GAP-017 — Streaming polling efficiency** (Resolved)  
  - Category: Ops | Severity: Low  
  - Evidence: Streaming endpoints poll every second (`backend/app/api/routes/streaming.py:48-66,94-110,208-223`) instead of event-driven updates.  
  - Description: WebSocket streaming endpoints now rely on event broadcasts (no DB polling) and stay open until client disconnects; backpressure via connection caps/timeouts.  
  - Suggested Next Action: Move SSE to event-driven and add heartbeat/metrics for streaming load.

- **GAP-022 — ROCm environment reproducibility** (Open)  
  - Category: DevEx/Ops | Severity: Low  
  - Evidence: ROCm artifacts documented in `ROCM_INTEGRATION_MAP.md` but no Nix shell for ROCm setup.  
  - Description: Developers need a reproducible environment to use local ROCm binaries/wheels.  
  - Suggested Next Action: Use `nix/rocm-shell.nix` as a ROCm-focused shell; extend flake to expose it and add scripts for loading vLLM image/binaries.

- **GAP-023 — Enforce Nix dev shell usage** (Open)  
  - Category: DevEx | Severity: Low  
  - Evidence: Guardrail script added (`tools/require-nix.sh`) and docs updated, but commands outside Nix are not automatically blocked.  
  - Description: Risk of running commands in ad-hoc environments; need enforcement for CI/local tooling.  
  - Suggested Next Action: Wire `tools/require-nix.sh` into CI scripts/package.json targets; update flake outputs to expose ROCm shell as `nix develop .#rocm`.

- **GAP-018 — Project intel service TODO patterns** (Resolved)  
  - Category: Implementation | Severity: Low  
  - Evidence: Placeholder comment “Generic patterns for TODO / future work.” (`backend/app/services/project_intel_service.py:129`).  
  - Description: Comment clarified as heuristic patterns for roadmap intent; heuristic extraction is intentionally simple.  
  - Suggested Next Action: Add tests for heuristic extraction and consider planner/embedding refinements.

- **GAP-019 — Roadmap/mission control enums partially defined** (Resolved)  
  - Category: Data/Spec | Severity: Low  
  - Evidence: `MissionControlTaskColumn`/`IdeaTicketStatus` enums include `TODO`/`BACKLOG` values but related behaviors/routes undocumented (`backend/app/domain/models.py:265-303`).  
  - Description: Backend ideas/intel spec now documents expected column/ticket lifecycles; enums align with code.  
  - Suggested Next Action: Add validation tests enforcing allowed transitions.

- **GAP-020 — Legacy specs with unresolved TBDs for workflow service** (Resolved)  
  - Category: Spec | Severity: Low  
  - Evidence: `docs/specs/test-specs/backend/test-spec-workflow-service.md:95,231` (related runs cascade TBD, locking TBD).  
  - Description: Workflow service test spec clarified: graph deletion is blocked when runs exist; status updates are last-write-wins (no optimistic locking).  
  - Suggested Next Action: Implement delete-graph guard and add concurrency tests.

- **GAP-021 — Ingest update writes message to error field** (Resolved)  
  - Category: Implementation | Severity: Low  
  - Evidence: `backend/app/services/ingest_service.py:272-283` sets `error_message` when `message` is provided.  
  - Description: Ingest jobs now persist `message` separately from `error_message`, and schema includes a dedicated `message` column.  
  - Suggested Next Action: Add tests to assert message/error separation in responses.

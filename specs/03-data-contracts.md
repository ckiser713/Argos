## Core Entities (SQLite Schema Alignment)
- **projects**: `{id PK, slug unique, name, description?, status, created_at, updated_at, default_model_role_id?, root_idea_cluster_id?, roadmap_id?}` (`backend/app/db.py:39-53`).
- **ingest_sources**: `{id PK, project_id FK, kind, name, description?, uri?, created_at, updated_at}`.
- **ingest_jobs**: `{id PK, project_id FK, source_id FK, original_filename, byte_size?, mime_type?, is_deep_scan bool, stage, progress, status, created_at, updated_at, completed_at?, error_message?, canonical_document_id?}`.
- **idea_candidates**: `{id PK, project_id FK, source_id FK, source_doc_id, source_doc_chunk_id, original_text, summary, embedding_json?, cluster_id?, created_at}`.
- **idea_clusters**: `{id PK, project_id FK, name, summary, idea_ids_json, created_at, updated_at}`.
- **idea_tickets**: `{id PK, project_id FK, cluster_id?, title, description?, status, priority, created_at, updated_at, origin_idea_ids_json}`.
- **knowledge_nodes/edges**: nodes `{id PK, project_id FK, title, summary?, tags_json, type}`; edges `{id PK, project_id FK, source FK, target FK, type, weight?, label?, created_at}`.
- **agent_runs/steps/messages/node_states**: runs `{id PK, project_id FK, agent_id, status, input_prompt?, output_summary?, started_at, finished_at?}`; steps `{id PK, run_id FK, step_number, node_id?, status, input_json?, output_json?, error?, duration_ms?, started_at, completed_at?}`; messages `{id PK, run_id FK, role, content, context_item_ids_json?, created_at}`; node_states `{run_id PK, node_id PK, status, progress, messages_json?, started_at?, completed_at?, error?}`.
- **workflow_graphs/runs/node_states**: graphs `{id PK, project_id FK, name, description?, graph_json, created_at, updated_at}`; runs `{id PK, project_id FK, workflow_id FK, status, input_json?, output_json?, started_at, finished_at?, last_message?, task_id?, checkpoint_json?, paused_at?, cancelled_at?, estimated_completion?}`; node_states similar to agent_node_states.
- **roadmap_nodes/edges**: nodes `{id PK, project_id FK, label, description?, status, priority?, start_date?, target_date?, depends_on_ids_json, lane_id?, idea_id?, ticket_id?, mission_control_task_id?, created_at, updated_at}`; edges `{id PK, project_id FK, from_node_id FK, to_node_id FK, kind, label?, created_at}`.
- **context_items**: `{id PK, project_id FK, name, type, tokens, pinned, canonical_document_id?, created_at}`.
- **workflow/agent/gap analysis reports**: `workflow_*` above; `gap_reports {id PK, project_id FK, generated_at}`; `gap_suggestions {id PK, report_id FK, project_id FK, ticket_id FK, status, notes, confidence, related_files_json}`.

## API Data Contracts (selected)
- Project: see `backend-projects-and-mode.md`; camelCase in responses (Pydantic aliases).
- IngestJob: fields per domain model (`status queued|running|completed|failed|cancelled`, `progress 0..1`, `stage`, `message/error_message?`, `canonical_document_id?`), though DB stores byte_size/mime_type/is_deep_scan not returned.
- KnowledgeNode/Edge: as per domain models; tags serialized from JSON.
- WorkflowGraph: `{id,name,description?,nodes[{id,label,x,y}],edges[{id,source,target}]}`; WorkflowRun: `{id,workflow_id,status,started_at,finished_at?,last_message?,task_id?,paused_at?,cancelled_at?}`; node states currently omit messages/error/timestamps in service mapper.
- AgentRun/Step/Message/NodeState: see domain models; note agent profiles limited to hardcoded ids.
- Idea entities: IdeaCandidate/Cluster/Ticket/MissionControlTask mapped from DB with some defaults; task description encoded in ticket.description JSON.
- Roadmap: RoadmapNode/Edge with status/priority enums; depends_on_ids array.
- Context: ContextBudget `{project_id,total_tokens,used_tokens,available_tokens,items[]}` with fixed total 100000; ContextItem fields per domain.

## Vector/RAG Contracts
- Qdrant collection `cortex_vectors` with payload `{content, **metadata}`; embeddings size 384 (SentenceTransformers all-MiniLM-L6-v2).
- Knowledge Qdrant upsert uses node title/summary/text/type; search returns node_ids + scores; metadata similarity_score added in responses.

## Serialization/Conventions
- Many Pydantic models use snake_case; some responses camelCase via alias (e.g., Project). Ensure frontend types match actual responses.
- Dates stored as ISO8601 strings in SQLite and returned as datetime objects serialized by FastAPI.

## Versioning & Migration
- No schema versioning; `init_db` creates tables if missing. Changes require manual migration.
- No API versioning beyond `/api` prefix.

## Risks & Gaps
- DB ↔ domain mismatches (workflow node state fields dropped; idea candidate status/confidence hardcoded).
- No foreign key enforcement in services; potential orphans.
- No explicit contract for error shapes; 400/404/409 used inconsistently.
- Vector store not multi-tenant; metadata schema ad-hoc.

## Verification Ideas
- Contract tests comparing API responses to domain/DB expectations (fields present, types/enums valid).
- Schema-to-model alignment checks (detect missing/extra fields).
- Define error response schema and test across routes.

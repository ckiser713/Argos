# Project Cortex: Comprehensive Granular Deep Dive Analysis

## BACKEND CORE ARCHITECTURE

### Application Initialization (`backend/app/main.py`)

The FastAPI application is constructed through a factory function `create_app()` that returns a configured FastAPI instance. Line 25-67 defines this factory pattern.

**Settings Loading (Line 26):** `get_settings()` is called from `app.config`, which uses `@lru_cache(maxsize=1)` decorator ensuring singleton Settings instance across the application lifecycle. This prevents redundant environment variable parsing.

**Database Initialization (Line 27):** `init_db()` is invoked synchronously during app creation. This executes the SQLite schema creation script defined in `backend/app/db.py`, lines 36-348. The database file path is determined by `settings.atlas_db_path` which defaults to `Path("atlas.db")` (relative to working directory).

**FastAPI Instance Creation (Lines 29-34):** The app is instantiated with:
- `title=settings.app_name` (defaults to "Cortex Backend")
- `version="0.1.0"` (hardcoded)
- `docs_url="/api/docs"` (Swagger UI)
- `redoc_url="/api/redoc"` (ReDoc)

**CORS Middleware Configuration (Lines 37-43):** CORSMiddleware is added with permissive settings:
- `allow_origins=settings.allowed_origins` defaults to `["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]`
- `allow_credentials=True` enables cookie/auth header forwarding
- `allow_methods=["*"]` allows all HTTP methods
- `allow_headers=["*"]` allows all headers

**Authentication Dependency Injection (Lines 45-49):** Conditional auth enforcement:
- If `settings.debug` is True OR `getattr(settings, 'skip_auth', False)` is True, `auth_deps = []` (no auth required)
- Otherwise, `auth_deps = [Depends(verify_token)]` where `verify_token` is imported from `app.services.auth_service`

**Router Registration (Lines 52-65):** Fourteen route modules are registered:
1. `auth.router` at `/api` - no auth required (login endpoint)
2. `system.router` at `/api` - requires auth
3. `projects.router` at `/api` - requires auth
4. `context.router` at `/api` - requires auth
5. `workflows.router` at `/api` - requires auth
6. `ingest.router` at `/api` - requires auth
7. `agents.router` at `/api` - requires auth
8. `knowledge.router` at `/api` - requires auth
9. `streaming.router` at `/api/stream` - requires auth (note different prefix)
10. `project_intel.router` at `/api` - requires auth
11. `mode.router` at `/api` - requires auth
12. `gap_analysis.router` at `/api` - requires auth
13. `roadmap.router` at `/api` - requires auth
14. `ideas.router` at `/api` - requires auth

**Module-Level App Instance (Line 70):** `app = create_app()` creates the singleton instance imported by uvicorn.

**Direct Execution Entry Point (Lines 73-76):** When run as `__main__`, uvicorn starts with:
- `host="0.0.0.0"` (binds to all interfaces)
- `port=8000`
- `reload=True` (auto-reload on code changes)

### Configuration Management (`backend/app/config.py`)

**Settings Class Definition (Lines 9-44):** `Settings` extends `BaseSettings` from `pydantic_settings`, enabling environment variable injection with validation.

**Application Metadata (Lines 10-12):**
- `app_name: str = Field(default="Cortex Backend")` - no env override
- `debug: bool = Field(default=False)` - no env override
- `skip_auth: bool = Field(default=False, env="CORTEX_SKIP_AUTH")` - can be set via `CORTEX_SKIP_AUTH` env var

**CORS Origins (Lines 13-19):** `allowed_origins: List[str]` uses `default_factory=lambda` to create a new list instance each time (avoiding mutable default argument anti-pattern). Defaults include Vite dev server (5173) and Create React App (3000).

**Database Paths (Lines 21-22):**
- `atlas_db_path: str = Field(default=str(Path("atlas.db")))` - main SQLite database
- `atlas_checkpoints_db_path: str = Field(default=str(Path("atlas_checkpoints.db")))` - LangGraph checkpoint storage (not currently used in db.py schema)

**LLM Configuration (Lines 24-27):**
- `llm_base_url: str = Field(default="http://localhost:11434/v1", env="CORTEX_LLM_BASE_URL")` - defaults to Ollama local instance
- `llm_api_key: str = Field(default="ollama", env="CORTEX_LLM_API_KEY")` - Ollama default key
- `llm_model_name: str = Field(default="llama3", env="CORTEX_LLM_MODEL")` - default model

**Execution Mode Defaults - Normal (Lines 29-32):**
- `normal_mode_llm_temperature: float = Field(0.2, env="CORTEX_NORMAL_TEMP")` - low temperature for deterministic output
- `normal_mode_validation_passes: int = Field(1, env="CORTEX_NORMAL_VALIDATION_PASSES")` - single pass
- `normal_mode_max_parallel_tools: int = Field(8, env="CORTEX_NORMAL_MAX_PARALLEL_TOOLS")` - allows 8 concurrent tool executions

**Execution Mode Defaults - Paranoid (Lines 34-37):**
- `paranoid_mode_llm_temperature: float = Field(0.1, env="CORTEX_PARANOID_TEMP")` - even lower temperature
- `paranoid_mode_validation_passes: int = Field(3, env="CORTEX_PARANOID_VALIDATION_PASSES")` - triple validation
- `paranoid_mode_max_parallel_tools: int = Field(3, env="CORTEX_PARANOID_MAX_PARALLEL_TOOLS")` - reduced parallelism

**Authentication Secret (Line 39):** `auth_secret: str = Field(default="a_very_secret_key", env="CORTEX_AUTH_SECRET")` - JWT signing key (MUST be changed in production).

**Qdrant Configuration (Line 42):** `qdrant_url: str = Field(default="http://localhost:6333", env="CORTEX_QDRANT_URL")` - vector database endpoint.

**Settings Config (Line 44):** `model_config = SettingsConfigDict(env_prefix="CORTEX_", env_file=None)` - all env vars prefixed with `CORTEX_`, no `.env` file loading (must use system env vars).

**Settings Singleton (Lines 47-49):** `@lru_cache(maxsize=1)` ensures only one Settings instance exists. Cache is never invalidated, so runtime env var changes won't be reflected (requires app restart).

### Database Layer (`backend/app/db.py`)

**Database Path Resolution (Lines 11-15):** `_db_path()` function:
- Retrieves `settings.atlas_db_path` via `get_settings()`
- Expands user home directory (`~`) if present using `Path.expanduser()`
- Creates parent directories with `path.parent.mkdir(parents=True, exist_ok=True)`
- Returns `Path` object

**Connection Factory (Lines 18-21):** `get_connection()`:
- Creates SQLite connection with `sqlite3.connect(_db_path(), check_same_thread=False)`
- `check_same_thread=False` allows connection sharing across threads (required for FastAPI async context)
- Sets `row_factory=sqlite3.Row` enabling dict-like row access (`row["column"]`)
- Returns connection without closing (caller responsible)

**Context Manager (Lines 24-30):** `db_session()` context manager:
- Yields connection from `get_connection()`
- Ensures `conn.close()` in `finally` block
- Used with `with db_session() as conn:` pattern throughout codebase

**Schema Initialization (Lines 33-350):** `init_db()` executes single `executescript()` call with 348 lines of SQL.

**WAL Mode (Line 38):** `PRAGMA journal_mode=WAL;` enables Write-Ahead Logging for better concurrency (multiple readers don't block writers).

**Projects Table (Lines 39-52):**
- `id TEXT PRIMARY KEY` - UUID strings
- `slug TEXT UNIQUE` - URL-friendly identifier
- `name TEXT NOT NULL` - display name
- `description TEXT` - nullable
- `status TEXT NOT NULL` - enum-like string (active/archived/draft)
- `created_at TEXT NOT NULL` - ISO datetime string
- `updated_at TEXT NOT NULL` - ISO datetime string
- `default_model_role_id TEXT` - nullable reference (not used in current schema)
- `root_idea_cluster_id TEXT` - nullable reference to idea_clusters
- `roadmap_id TEXT` - nullable reference to roadmaps
- Indexes: `idx_projects_status`, `idx_projects_slug`

**Ingest Sources Table (Lines 54-65):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `kind TEXT NOT NULL` - enum: file/folder/repo/chat_export/url/manual_note
- `name TEXT NOT NULL` - display name
- `description TEXT` - nullable
- `uri TEXT` - nullable file path or URL
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- Index: `idx_ingest_sources_project`

**Ingest Jobs Table (Lines 67-87):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `source_id TEXT NOT NULL` - FK to ingest_sources
- `original_filename TEXT NOT NULL`
- `byte_size INTEGER NOT NULL DEFAULT 0`
- `mime_type TEXT` - nullable
- `is_deep_scan INTEGER NOT NULL DEFAULT 0` - boolean flag (0/1)
- `stage TEXT NOT NULL` - pipeline stage string
- `progress REAL NOT NULL DEFAULT 0` - 0.0 to 1.0
- `status TEXT NOT NULL` - enum: queued/running/completed/failed/cancelled
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `completed_at TEXT` - nullable
- `error_message TEXT` - nullable
- `canonical_document_id TEXT` - nullable reference (not in current schema)
- Indexes: `idx_ingest_jobs_project`, `idx_ingest_jobs_source`

**Idea Tickets Table (Lines 89-102):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `cluster_id TEXT` - nullable FK to idea_clusters
- `title TEXT NOT NULL`
- `description TEXT` - nullable
- `status TEXT NOT NULL` - enum: active/complete/blocked
- `priority TEXT NOT NULL` - enum: low/medium/high
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- `origin_idea_ids_json TEXT` - JSON array of idea candidate IDs
- Index: `idx_idea_tickets_project`

**Knowledge Nodes Table (Lines 104-113):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `title TEXT NOT NULL`
- `summary TEXT` - nullable
- `tags_json TEXT` - JSON array of tag strings
- `type TEXT NOT NULL` - node type string
- Index: `idx_knowledge_nodes_project`

**Agent Runs Table (Lines 115-126):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `agent_id TEXT NOT NULL` - references agent profile ID
- `status TEXT NOT NULL` - enum: pending/running/completed/failed/cancelled
- `input_prompt TEXT` - nullable user prompt
- `output_summary TEXT` - nullable final output
- `started_at TEXT NOT NULL`
- `finished_at TEXT` - nullable
- Index: `idx_agent_runs_project`

**Idea Candidates Table (Lines 128-143):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `source_id TEXT NOT NULL` - FK to ingest_sources
- `source_doc_id TEXT NOT NULL` - reference to canonical document (not in schema)
- `source_doc_chunk_id TEXT NOT NULL` - reference to chunk (not in schema)
- `original_text TEXT NOT NULL` - extracted text
- `summary TEXT NOT NULL` - LLM-generated summary
- `embedding_json TEXT` - JSON array of floats (vector embedding)
- `cluster_id TEXT` - nullable FK to idea_clusters
- `created_at TEXT NOT NULL`
- Indexes: `idx_idea_candidates_project`, `idx_idea_candidates_cluster`

**Idea Clusters Table (Lines 145-155):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `name TEXT NOT NULL`
- `summary TEXT NOT NULL`
- `idea_ids_json TEXT` - JSON array of idea candidate IDs
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- Index: `idx_idea_clusters_project`

**Roadmaps Table (Lines 157-166):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `name TEXT NOT NULL`
- `graph_json TEXT` - JSON serialized roadmap graph (legacy, replaced by roadmap_nodes/edges)
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- Index: `idx_roadmaps_project`

**Context Items Table (Lines 168-180):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `name TEXT NOT NULL`
- `type TEXT NOT NULL` - enum: pdf/repo/chat/other
- `tokens INTEGER NOT NULL DEFAULT 0` - token count for budget tracking
- `pinned INTEGER NOT NULL DEFAULT 0` - boolean flag (0/1)
- `canonical_document_id TEXT` - nullable reference (not in schema)
- `created_at TEXT NOT NULL`
- Indexes: `idx_context_items_project`, `idx_context_items_pinned`

**Agent Steps Table (Lines 182-197):**
- `id TEXT PRIMARY KEY`
- `run_id TEXT NOT NULL` - FK to agent_runs
- `step_number INTEGER NOT NULL` - sequential step index
- `node_id TEXT` - nullable LangGraph node identifier
- `status TEXT NOT NULL` - enum: pending/running/completed/failed
- `input_json TEXT` - nullable JSON serialized input
- `output_json TEXT` - nullable JSON serialized output
- `error TEXT` - nullable error message
- `duration_ms INTEGER` - nullable execution time in milliseconds
- `started_at TEXT NOT NULL`
- `completed_at TEXT` - nullable
- Indexes: `idx_agent_steps_run`, `idx_agent_steps_step_number` (composite)

**Agent Messages Table (Lines 199-209):**
- `id TEXT PRIMARY KEY`
- `run_id TEXT NOT NULL` - FK to agent_runs
- `role TEXT NOT NULL` - enum: user/assistant/system
- `content TEXT NOT NULL` - message text
- `context_item_ids_json TEXT` - JSON array of context item IDs
- `created_at TEXT NOT NULL`
- Indexes: `idx_agent_messages_run`, `idx_agent_messages_created_at` (composite for chronological ordering)

**Agent Node States Table (Lines 211-223):**
- Composite PRIMARY KEY: `(run_id, node_id)`
- `run_id TEXT NOT NULL` - FK to agent_runs
- `node_id TEXT NOT NULL` - LangGraph node identifier
- `status TEXT NOT NULL` - node execution status string
- `progress REAL NOT NULL DEFAULT 0` - 0.0 to 1.0
- `messages_json TEXT` - JSON array of status messages
- `started_at TEXT` - nullable ISO datetime
- `completed_at TEXT` - nullable ISO datetime
- `error TEXT` - nullable error message
- Index: `idx_agent_node_states_run`

**Workflow Graphs Table (Lines 225-235):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `name TEXT NOT NULL`
- `description TEXT` - nullable
- `graph_json TEXT NOT NULL` - JSON serialized WorkflowGraph (nodes + edges)
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- Index: `idx_workflow_graphs_project`

**Workflow Runs Table (Lines 237-257):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `workflow_id TEXT NOT NULL` - FK to workflow_graphs
- `status TEXT NOT NULL` - enum: pending/running/completed/failed/cancelled/paused
- `input_json TEXT` - nullable JSON serialized input data
- `output_json TEXT` - nullable JSON serialized output data
- `started_at TEXT NOT NULL`
- `finished_at TEXT` - nullable
- `last_message TEXT` - nullable status message
- `task_id TEXT` - nullable background task identifier
- `checkpoint_json TEXT` - nullable JSON serialized checkpoint state (for pause/resume)
- `paused_at TEXT` - nullable ISO datetime
- `cancelled_at TEXT` - nullable ISO datetime
- `estimated_completion TEXT` - nullable ISO datetime
- Indexes: `idx_workflow_runs_project`, `idx_workflow_runs_status`, `idx_workflow_runs_task_id`

**Workflow Node States Table (Lines 259-271):**
- Composite PRIMARY KEY: `(run_id, node_id)`
- `run_id TEXT NOT NULL` - FK to workflow_runs
- `node_id TEXT NOT NULL` - workflow node identifier
- `status TEXT NOT NULL` - node execution status
- `progress REAL NOT NULL DEFAULT 0` - 0.0 to 1.0
- `messages_json TEXT` - JSON array of status messages
- `started_at TEXT` - nullable
- `completed_at TEXT` - nullable
- `error TEXT` - nullable
- Index: `idx_workflow_node_states_run`

**Roadmap Nodes Table (Lines 273-292):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `label TEXT NOT NULL` - display label
- `description TEXT` - nullable
- `status TEXT NOT NULL` - enum: pending/active/complete/blocked
- `priority TEXT` - nullable enum: low/medium/high
- `start_date TEXT` - nullable ISO date
- `target_date TEXT` - nullable ISO date
- `depends_on_ids_json TEXT` - JSON array of roadmap node IDs (dependency list)
- `lane_id TEXT` - nullable grouping identifier
- `idea_id TEXT` - nullable FK to idea_candidates
- `ticket_id TEXT` - nullable FK to idea_tickets
- `mission_control_task_id TEXT` - nullable reference (not in schema)
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`
- Indexes: `idx_roadmap_nodes_project`, `idx_roadmap_nodes_status`

**Roadmap Edges Table (Lines 294-308):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `from_node_id TEXT NOT NULL` - FK to roadmap_nodes
- `to_node_id TEXT NOT NULL` - FK to roadmap_nodes
- `kind TEXT NOT NULL` - enum: depends_on/relates_to
- `label TEXT` - nullable edge label
- `created_at TEXT NOT NULL`
- Indexes: `idx_roadmap_edges_project`, `idx_roadmap_edges_from`, `idx_roadmap_edges_to`

**Knowledge Edges Table (Lines 310-325):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `source TEXT NOT NULL` - FK to knowledge_nodes.id
- `target TEXT NOT NULL` - FK to knowledge_nodes.id
- `type TEXT NOT NULL` - relationship type string
- `weight REAL` - nullable edge weight (0.0 to 1.0)
- `label TEXT` - nullable edge label
- `created_at TEXT NOT NULL`
- Indexes: `idx_knowledge_edges_project`, `idx_knowledge_edges_source`, `idx_knowledge_edges_target`

**Gap Reports Table (Lines 327-333):**
- `id TEXT PRIMARY KEY`
- `project_id TEXT NOT NULL` - FK to projects
- `generated_at TEXT NOT NULL` - ISO datetime
- Index: `idx_gap_reports_project`

**Gap Suggestions Table (Lines 335-347):**
- `id TEXT PRIMARY KEY`
- `report_id TEXT NOT NULL` - FK to gap_reports
- `project_id TEXT NOT NULL` - FK to projects (denormalized for query efficiency)
- `ticket_id TEXT NOT NULL` - FK to idea_tickets
- `status TEXT NOT NULL` - suggestion status string
- `notes TEXT NOT NULL` - suggestion description
- `confidence REAL NOT NULL` - 0.0 to 1.0 confidence score
- `related_files_json TEXT` - JSON array of file paths
- Index: `idx_gap_suggestions_report`

**Schema Commit (Line 350):** `conn.commit()` finalizes all CREATE TABLE and CREATE INDEX statements atomically.

---

## Backend Repository Layer Analysis

The repository layer (`backend/app/repos/`) implements data access patterns for domain entities, abstracting SQLite operations behind clean interfaces. Five repository modules provide CRUD operations and query logic.

### ProjectRepository (`backend/app/repos/project_repo.py`)

**Class Definition (Lines 12-115):** `ProjectRepository` provides CRUD operations for `CortexProject` entities.

**List Projects (Lines 13-28):** `list_projects(cursor, limit)` implements cursor-based pagination:
- Uses integer offset from cursor string (line 14)
- Fetches `limit + 1` rows to detect next page (line 22)
- Returns `PaginatedResponse` with items, next_cursor, and total count (lines 24-28)
- Total count uses separate COUNT query (lines 26-27)

**Get Project (Lines 30-35):** `get_project(project_id)` fetches single project by ID:
- Returns `Optional[CortexProject]` (line 30)
- Uses parameterized query with single WHERE clause (line 32)

**Get By Slug (Lines 37-42):** `get_by_slug(slug)` retrieves project by unique slug:
- Uses UNIQUE constraint on `slug` column (line 39)
- Returns `None` if not found (lines 40-41)

**Save Project (Lines 44-67):** `save(project)` inserts new project:
- Executes INSERT with all project fields (lines 48-51)
- Converts datetime objects to ISO strings (lines 59-60)
- Commits transaction atomically (line 66)

**Update Project (Lines 69-95):** `update(project_id, fields)` performs partial updates:
- Filters allowed fields (lines 72-79)
- Builds dynamic SET clause from updates dict (line 84)
- Always updates `updated_at` timestamp (line 86)
- Returns updated project via `get_project` (line 95)

**Delete Project (Lines 97-101):** `delete(project_id)` removes project:
- Returns boolean indicating success (line 101)
- Uses `rowcount` to verify deletion (line 100)

**Row to Model Conversion (Lines 103-115):** `_row_to_model(row)` converts SQLite Row to `CortexProject`:
- Parses ISO datetime strings (lines 110-111)
- Handles nullable fields (lines 112-114)

**Singleton Accessor (Lines 118-119):** `get_project_repo()` returns singleton `ProjectRepository` instance.

### ModeRepository (`backend/app/repos/mode_repo.py`)

**In-Memory Storage (Lines 11-13):** `_PROJECT_SETTINGS_STORE` is a `Dict[str, ProjectExecutionSettings]` mapping project_id to execution settings. This is temporary; production would use database persistence.

**Default Settings Builder (Lines 16-36):** `_build_default_settings(project_id, mode)` creates default `ProjectExecutionSettings`:
- Reads global settings via `get_settings()` (line 18)
- Returns paranoid mode settings if mode is "paranoid" (lines 20-27)
- Returns normal mode settings otherwise (lines 30-35)
- Includes temperature, validation_passes, max_parallel_tools from config

**Get Project Settings (Lines 39-62):** `get_project_settings(project_id)` fetches or creates default settings:
- Checks in-memory store first (line 46)
- Creates default if missing (lines 49-50)
- Logs settings creation (lines 52-61)
- Returns cached settings (line 62)

**Set Project Settings (Lines 65-84):** `set_project_settings(new_settings)` upserts settings:
- Stores in `_PROJECT_SETTINGS_STORE` (line 72)
- Logs update with all fields (lines 74-83)
- Returns the stored settings (line 84)

**Design Note:** This repository uses in-memory storage for performance (O(1) lookups) but lacks persistence. Future migration to database-backed storage should maintain caching layer.

### GapAnalysisRepository (`backend/app/repos/gap_analysis_repo.py`)

**Protocol Definition (Lines 15-20):** `GapAnalysisRepo` protocol defines async interface:
- `save_gap_report(report)` persists report and suggestions
- `get_latest_gap_report(project_id)` retrieves most recent report
- `list_gap_reports(project_id, limit)` lists historical reports

**SQLite Implementation (Lines 23-159):** `SqliteGapAnalysisRepo` implements protocol with SQLite backend.

**Save Gap Report (Lines 28-71):** `save_gap_report(report)` persists report atomically:
- Generates UUID for report_id (line 34)
- Inserts report header into `gap_reports` table (lines 38-47)
- Inserts each suggestion into `gap_suggestions` table (lines 51-68)
- Serializes `related_files` list as JSON (line 66)
- Commits transaction (line 69)
- Logs completion (line 71)

**Get Latest Gap Report (Lines 73-113):** `get_latest_gap_report(project_id)` retrieves most recent report:
- Queries `gap_reports` ordered by `generated_at DESC` (lines 76-83)
- Returns `None` if no reports exist (lines 85-86)
- Fetches associated suggestions (lines 92-94)
- Deserializes JSON fields (line 104)
- Constructs `GapReport` with suggestions (lines 109-113)

**List Gap Reports (Lines 115-158):** `list_gap_reports(project_id, limit)` lists historical reports:
- Queries reports ordered by `generated_at DESC` (lines 118-125)
- For each report, queries suggestions separately (lines 132-135)
- Deserializes JSON and constructs `GapReport` objects (lines 137-155)
- Returns list sorted newest-first (implicit via ORDER BY)

**Singleton Accessor (Lines 161-167):** `get_gap_analysis_repo()` returns singleton `SqliteGapAnalysisRepo` instance.

**Performance Note:** `list_gap_reports` performs N+1 queries (one per report for suggestions). Consider JOIN or batch loading for optimization.

### RoadmapRepository (`backend/app/repos/roadmap_repo.py`)

**Save Roadmap (Lines 11-28):** `save_roadmap(roadmap)` upserts roadmap:
- Uses `INSERT OR REPLACE` for idempotency (line 15)
- Serializes `graph` dict as JSON (line 23)
- Stores ISO datetime strings (lines 24-25)

**Get Roadmap (Lines 31-43):** `get_roadmap(roadmap_id)` retrieves single roadmap:
- Deserializes `graph_json` to dict (line 39)
- Parses ISO datetime strings (lines 40-41)
- Returns `None` if not found (line 43)

**Get Roadmaps For Project (Lines 46-59):** `get_roadmaps_for_project(project_id)` lists all roadmaps for project:
- Returns list of `Roadmap` objects (line 49)
- Deserializes JSON and datetime fields (lines 50-57)

**Design Note:** Roadmap repository uses simple CRUD pattern. Graph structure stored as JSON blob; no graph-specific query operations.

### ProjectIntelRepository (`backend/app/repos/project_intel_repo.py`)

**Save Candidates (Lines 23-53):** `save_candidates(candidates)` upserts batch of idea candidates:
- Uses `INSERT OR REPLACE` for each candidate (line 31)
- Serializes `embedding` list as JSON (line 44)
- Commits batch transaction (line 49)
- Logs count (lines 50-53)

**List Candidates (Lines 56-83):** `list_candidates(project_id)` lists candidates optionally filtered by project:
- Deserializes `embedding_json` to list (line 77)
- Returns sorted by id for determinism (line 82)

**Get Candidate (Lines 85-101):** `get_candidate(candidate_id)` retrieves single candidate:
- Deserializes JSON fields (line 97)
- Returns `None` if not found (line 101)

**Save Clusters (Lines 107-130):** `save_clusters(clusters)` upserts batch of idea clusters:
- Serializes `idea_ids` list as JSON (line 121)
- Commits batch transaction (line 126)
- Logs count (lines 127-130)

**List Clusters (Lines 133-154):** `list_clusters(project_id)` lists clusters optionally filtered by project:
- Deserializes `idea_ids_json` to list (line 148)
- Returns sorted by name for determinism (line 154)

**Save Tickets (Lines 160-192):** `save_tickets(tickets)` and `save_ticket(ticket)` upsert tickets:
- Serializes `origin_idea_ids` list as JSON (line 188)
- Commits per-ticket (line 191)

**List Tickets (Lines 194-236):** `list_tickets(project_id)` lists tickets with custom sorting:
- Deserializes JSON fields (line 214)
- Sorts by status priority, then priority enum, then created_at, then id (lines 228-234)
- Uses status_order and priority_order dicts for deterministic ordering (lines 218-226)

**Update Ticket Status (Lines 258-278):** `update_ticket_status(ticket_id, status, priority)` updates ticket:
- Fetches existing ticket (line 263)
- Updates status and optional priority (lines 267-269)
- Updates `updated_at` timestamp (line 271)
- Saves via `save_ticket` (line 273)
- Logs update (lines 274-277)

**Repository Pattern Summary:** All repositories follow consistent patterns:
- Use `db_session()` context manager for connection handling
- Serialize complex types (lists, dicts) as JSON strings
- Parse ISO datetime strings to `datetime` objects
- Return domain models (`CortexProject`, `GapReport`, `Roadmap`, etc.)
- Handle `None` returns for not-found cases
- Use parameterized queries to prevent SQL injection

---

## Domain Models & Pydantic Schemas Analysis

The domain layer (`backend/app/domain/`) defines all Pydantic models used throughout the application for request/response validation, data transfer, and business logic. Seven domain modules provide comprehensive type definitions covering projects, context, workflows, ingestion, agents, ideas, roadmaps, knowledge graphs, gap analysis, project intelligence, execution modes, and system metrics.

### Common Domain Utilities (`backend/app/domain/common.py`)

**to_camel Function (Lines 8-10):**
- **Purpose:** Converts snake_case strings to camelCase for API serialization
- **Algorithm:** Splits on underscores, capitalizes subsequent words, joins without separators
- **Example:** `"next_cursor"` → `"nextCursor"`
- **Usage:** Used as `alias_generator` in Pydantic `ConfigDict` for API responses

**PaginatedResponse Model (Lines 13-18):**
- **Fields:**
  - `items: list` - List of items for current page (generic, not typed)
  - `next_cursor: Optional[str] = None` - Cursor for next page (null if last page)
  - `total: Optional[int] = None` - Total count across all pages (optional for performance)
- **Config:** Uses `to_camel` alias generator, `populate_by_name=True` allows both snake_case and camelCase
- **Usage:** Generic pagination wrapper used by all list endpoints

### Project Domain Models (`backend/app/domain/project.py`)

**CortexProjectStatus Enum (Lines 12-15):**
- **Values:** `ACTIVE`, `ARCHIVED`, `DRAFT`
- **String-Based:** Extends `str` and `Enum` for JSON serialization
- **Default:** `ACTIVE` used as default in `CortexProject`

**CortexProject Model (Lines 18-30):**
- **Required Fields:**
  - `id: str` - UUID string identifier
  - `slug: str` - URL-friendly identifier (unique)
  - `name: str` - Display name
  - `created_at: datetime` - Creation timestamp
  - `updated_at: datetime` - Last update timestamp
- **Optional Fields:**
  - `description: Optional[str] = None` - Project description
  - `status: CortexProjectStatus = Field(default=CortexProjectStatus.ACTIVE)` - Project status
  - `default_model_role_id: Optional[str] = None` - Reference to model role (not used)
  - `root_idea_cluster_id: Optional[str] = None` - Reference to root idea cluster
  - `roadmap_id: Optional[str] = None` - Reference to roadmap
- **Config:** Uses `to_camel` alias generator for API serialization, `populate_by_name=True` for flexibility

**CreateProjectRequest Model (Lines 33-38):**
- **Required Fields:** `name: str`
- **Optional Fields:** `slug: Optional[str] = None`, `description: Optional[str] = None`
- **Slug Generation:** If slug not provided, generated from name via `ProjectFactory._slugify()`
- **Config:** Uses camelCase aliases

**UpdateProjectRequest Model (Lines 41-49):**
- **All Fields Optional:** Supports partial updates
- **Fields:** `name?`, `description?`, `status?`, `default_model_role_id?`, `root_idea_cluster_id?`, `roadmap_id?`
- **Validation:** Status must be valid `CortexProjectStatus` enum value
- **Config:** Uses camelCase aliases

**DeleteProjectResponse Model (Lines 52-55):**
- **Fields:** `success: bool = True` - Always True if deletion succeeds
- **Config:** Uses camelCase aliases

**ProjectFactory Class (Lines 58-76):**
- **`new` Static Method (Lines 60-72):**
  - **Parameters:** `name: str`, `slug: Optional[str]`, `description: Optional[str]`
  - **ID Generation:** Uses `uuid4().hex` for 32-character hex ID (line 61)
  - **Slug Normalization:** Calls `_slugify(name)` if slug not provided (line 62)
  - **Timestamp Generation:** Uses `datetime.now(timezone.utc)` for UTC timestamps (line 63)
  - **Default Status:** Sets `status=CortexProjectStatus.ACTIVE` (line 69)
  - **Return:** `CortexProject` instance with all required fields populated
- **`_slugify` Static Method (Lines 74-76):**
  - **Algorithm:** Lowercases input, splits on whitespace, joins with hyphens
  - **Example:** `"My Project"` → `"my-project"`
  - **Usage:** Internal helper for slug generation

**Roadmap Model (Lines 79-87):**
- **Fields:**
  - `id: str` - Roadmap identifier
  - `project_id: str` - Project reference
  - `name: str` - Roadmap name
  - `graph: dict` - JSON-serialized graph structure (legacy, replaced by roadmap_nodes/edges)
  - `created_at: datetime` - Creation timestamp
  - `updated_at: datetime` - Update timestamp
- **Note:** Legacy model, roadmap now uses `RoadmapGraph` with nodes/edges lists

### Execution Mode Domain Models (`backend/app/domain/mode.py`)

**ExecutionMode Type Alias (Line 7):**
- **Type:** `Literal["normal", "paranoid"]`
- **Values:** Two execution modes with different validation/parallelism characteristics
- **Usage:** Type hint for mode field in `ProjectExecutionSettings`

**ProjectExecutionSettings Model (Lines 10-46):**
- **Purpose:** Per-project execution behavior configuration (lightweight, read on every LLM call)
- **Required Fields:**
  - `project_id: str` - Logical project identifier
- **Default Fields:**
  - `mode: ExecutionMode = Field("normal", ...)` - Execution mode (normal/paranoid)
  - `llm_temperature: float = Field(0.2, ge=0.0, le=2.0, ...)` - Base LLM temperature (0.0-2.0)
  - `validation_passes: int = Field(1, ge=1, le=10, ...)` - Number of validation passes (1-10)
  - `max_parallel_tools: int = Field(4, ge=1, le=64, ...)` - Maximum parallel tools/subtasks (1-64)
- **Validation:**
  - Temperature clamped to [0.0, 2.0] range
  - Validation passes clamped to [1, 10] range
  - Max parallel tools clamped to [1, 64] range
- **Design:** Intentionally lightweight for frequent reads during agent/LLM calls

### Gap Analysis Domain Models (`backend/app/domain/gap_analysis.py`)

**GapStatus Type Alias (Line 8):**
- **Type:** `Literal["unmapped", "partially_implemented", "implemented", "unknown"]`
- **Values:** Four status levels for gap analysis classification
- **Usage:** Type hint for status field in `GapSuggestion`

**GapSuggestion Model (Lines 11-25):**
- **Purpose:** Single suggestion describing how idea ticket maps to codebase
- **Required Fields:**
  - `id: str` - Suggestion identifier (format: `"{project_id}:{ticket_id}"`)
  - `project_id: str` - Project reference
  - `ticket_id: str` - Idea ticket reference
  - `status: GapStatus` - Classification status
  - `notes: str` - Human-readable notes describing gap/implementation
  - `confidence: float = Field(ge=0.0, le=1.0)` - Confidence score (0.0-1.0)
- **Optional Fields:**
  - `related_files: List[str] = Field(default_factory=list)` - List of related file paths
- **Config:** `extra = "ignore"` prevents unknown fields from causing validation errors

**GapReport Model (Lines 28-38):**
- **Purpose:** Aggregated gap analysis for project at point in time
- **Required Fields:**
  - `project_id: str` - Project reference
  - `generated_at: datetime` - Report generation timestamp
- **Optional Fields:**
  - `suggestions: List[GapSuggestion] = Field(default_factory=list)` - List of gap suggestions
- **Config:** `extra = "ignore"` for forward compatibility

### Project Intelligence Domain Models (`backend/app/domain/project_intel.py`)

**Type Aliases (Lines 8-12):**
- **`IdeaLabel`:** `str` - Label string for idea categorization
- **`EmbeddingVector`:** `List[float]` - Vector embedding representation
- **`IdeaTicketStatus`:** `Literal["candidate", "triaged", "planned", "in_progress", "done"]` - Ticket lifecycle status
- **`IdeaTicketPriority`:** `Literal["low", "medium", "high"]` - Ticket priority level

**IdeaCandidate Model (Lines 15-33):**
- **Purpose:** Raw idea extracted from chat segments, normalized for clustering
- **Required Fields:**
  - `id: str` - Deterministic ID from `_stable_id()` hash
  - `segment_id: str` - Source chat segment reference
  - `title: str` - First ~12 words of text
  - `summary: str` - First ~40 words of text
  - `confidence: float = Field(ge=0.0, le=1.0)` - Heuristic confidence score
- **Optional Fields:**
  - `project_id: Optional[str] = None` - Project reference
  - `labels: List[IdeaLabel] = Field(default_factory=list)` - Categorization labels
  - `source_chat_ids: List[str] = Field(default_factory=list)` - Traceability to source chats
- **Design:** Close to original language but normalized for clustering

**IdeaCluster Model (Lines 35-48):**
- **Purpose:** Semantic grouping of related IdeaCandidates
- **Required Fields:**
  - `id: str` - Cluster identifier
  - `name: str` - Cluster name (from highest-confidence candidate)
  - `idea_ids: List[str] = Field(default_factory=list)` - List of candidate IDs in cluster
- **Optional Fields:**
  - `project_id: Optional[str] = None` - Project reference
  - `centroid_embedding: Optional[EmbeddingVector] = None` - Cluster centroid embedding (for similarity)
- **Design:** Supports both embedding-based and label-based clustering

**IdeaTicket Model (Lines 50-69):**
- **Purpose:** Promotable ticket derived from IdeaCandidates/clusters, feeds into roadmap/mission control
- **Required Fields:**
  - `id: str` - Ticket identifier
  - `title: str` - Ticket title
  - `description: str` - Ticket description
  - `status: IdeaTicketStatus = "candidate"` - Ticket status (default: candidate)
  - `priority: IdeaTicketPriority = "medium"` - Ticket priority (default: medium)
- **Optional Fields:**
  - `project_id: Optional[str] = None` - Project reference
  - `cluster_id: Optional[str] = None` - Source cluster reference
  - `origin_idea_ids: List[str] = Field(default_factory=list)` - Source idea candidate IDs
  - `created_at: datetime` - Creation timestamp (auto-generated)
  - `updated_at: datetime` - Update timestamp (auto-generated)
- **Design:** Bridge between ideas and actionable tickets

### System Metrics Domain Models (`backend/app/domain/system_metrics.py`)

**GpuMetrics Model (Lines 8-18):**
- **Purpose:** Best-effort GPU metrics (fields may be None if unavailable)
- **Optional Fields:**
  - `name: Optional[str]` - GPU name/model (e.g., "AMD Radeon RX 7900 XTX")
  - `total_vram_gb: Optional[float]` - Total VRAM in GiB
  - `used_vram_gb: Optional[float]` - Used VRAM in GiB
  - `utilization_pct: Optional[float] = Field(None, ge=0.0, le=100.0)` - GPU utilization percentage (0-100)
- **Design:** Graceful degradation if GPU unavailable (ROCm-specific)

**CpuMetrics Model (Lines 20-24):**
- **Purpose:** Logical CPU load snapshot
- **Required Fields:**
  - `num_cores: int = Field(..., ge=1)` - Number of logical CPU cores (>= 1)
  - `load_pct: float = Field(..., ge=0.0, le=100.0)` - Overall CPU utilization percentage (0-100)
- **Design:** Always available (fallback to stdlib if psutil unavailable)

**MemoryMetrics Model (Lines 27-31):**
- **Purpose:** System memory metrics in GiB
- **Required Fields:**
  - `total_gb: float = Field(..., gt=0.0)` - Total system RAM in GiB (> 0)
  - `used_gb: float = Field(..., ge=0.0)` - Used RAM in GiB (>= 0)
- **Design:** Always available (fallback to /proc/meminfo if psutil unavailable)

**ContextMetrics Model (Lines 34-38):**
- **Purpose:** Logical token-budget view for Cortex runtime
- **Required Fields:**
  - `total_tokens: int = Field(..., ge=0)` - Total token budget (>= 0)
  - `used_tokens: int = Field(..., ge=0)` - Tokens currently consumed (>= 0)
- **Design:** Tracks context window usage across all projects

**SystemStatusLiteral Type Alias (Line 41):**
- **Type:** `Literal["nominal", "warning", "critical"]`
- **Values:** Three severity levels for overall system status
- **Usage:** Type hint for status field in `SystemStatus`

**SystemStatus Model (Lines 44-62):**
- **Purpose:** Aggregated view for Command Center header
- **Required Fields:**
  - `status: SystemStatusLiteral` - Overall system status (nominal/warning/critical)
  - `cpu: CpuMetrics` - CPU metrics
  - `memory: MemoryMetrics` - Memory metrics
  - `context: ContextMetrics` - Context metrics
  - `active_agent_runs: int = Field(..., ge=0)` - Number of currently active agent runs (>= 0)
- **Optional Fields:**
  - `reason: Optional[str]` - Human-readable summary of non-nominal status
  - `gpu: Optional[GpuMetrics]` - GPU metrics (None if no ROCm device)
- **Design:** Aggregates all metric sources, classifies overall status

### Core Domain Models (`backend/app/domain/models.py`)

**Context Models (Lines 12-46):**
- **`ContextItemType` Enum (Lines 15-19):** `PDF`, `REPO`, `CHAT`, `OTHER` - Context item source types
- **`ContextItem` Model (Lines 22-29):**
  - Required: `id`, `name`, `type: ContextItemType`, `tokens: int (ge=0)`
  - Optional: `pinned: bool = False`, `canonical_document_id`, `created_at`
- **`ContextBudget` Model (Lines 32-37):**
  - Required: `project_id`, `total_tokens`, `used_tokens`, `available_tokens`
  - Optional: `items: List[ContextItem] = Field(default_factory=list)`
- **`AddContextItemsRequest` Model (Lines 40-41):** `items: List[ContextItem]`
- **`AddContextItemsResponse` Model (Lines 44-46):** `items: List[ContextItem]`, `budget: ContextBudget`

**Workflow Models (Lines 49-106):**
- **`WorkflowNode` Model (Lines 52-56):** `id`, `label`, `x: float`, `y: float` - Visual node position
- **`WorkflowEdge` Model (Lines 59-62):** `id`, `source`, `target` - Edge connection
- **`WorkflowGraph` Model (Lines 65-70):** `id`, `name`, `description?`, `nodes: List[WorkflowNode]`, `edges: List[WorkflowEdge]`
- **`WorkflowRunStatus` Enum (Lines 73-79):** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `PAUSED`
- **`WorkflowRun` Model (Lines 82-91):**
  - Required: `id`, `workflow_id`, `status: WorkflowRunStatus`, `started_at: datetime`
  - Optional: `finished_at`, `last_message`, `task_id`, `paused_at`, `cancelled_at`
- **`WorkflowNodeStatus` Enum (Lines 94-99):** `IDLE`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
- **`WorkflowNodeState` Model (Lines 102-105):** `node_id`, `status: WorkflowNodeStatus`, `progress: float (ge=0.0, le=1.0)`

**Ingestion Models (Lines 108-139):**
- **`IngestStatus` Enum (Lines 111-116):** `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
- **`IngestJob` Model (Lines 119-134):**
  - Required: `id`, `source_path: str`, `created_at: datetime`, `status: IngestStatus`, `progress: float (ge=0.0, le=1.0)`
  - Optional: `project_id`, `original_filename`, `byte_size`, `mime_type`, `stage`, `updated_at`, `completed_at`, `message`, `error_message`, `canonical_document_id`
- **`IngestRequest` Model (Lines 137-138):** `source_path: str` (required, with description)

**Agent Models (Lines 141-230):**
- **`AgentProfile` Model (Lines 144-148):** `id`, `name`, `description?`, `capabilities: List[str]`
- **`AgentRunStatus` Enum (Lines 151-156):** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`
- **`AgentRun` Model (Lines 159-170):**
  - Required: `id`, `project_id`, `agent_id`, `status: AgentRunStatus`, `started_at: datetime`
  - Optional: `workflow_id`, `input_query`, `input_prompt`, `output_summary`, `context_item_ids: List[str]`, `finished_at`
- **`AgentRunRequest` Model (Lines 173-177):** `project_id`, `agent_id`, `input_prompt`, `context_item_ids?`
- **`AgentStepStatus` Enum (Lines 180-184):** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
- **`AgentStep` Model (Lines 187-198):**
  - Required: `id`, `run_id`, `step_number: int`, `status: AgentStepStatus`, `started_at: datetime`
  - Optional: `node_id`, `input`, `output`, `error`, `duration_ms`, `completed_at`
- **`AgentMessageRole` Enum (Lines 201-204):** `USER`, `ASSISTANT`, `SYSTEM`
- **`AgentMessage` Model (Lines 207-213):** `id`, `run_id`, `role: AgentMessageRole`, `content`, `context_item_ids: List[str]`, `created_at`
- **`AgentNodeState` Model (Lines 216-224):**
  - Required: `run_id`, `node_id`, `status: str`, `progress: float (ge=0.0, le=1.0)`, `messages: List[str]`
  - Optional: `started_at`, `completed_at`, `error`
- **`AppendMessageRequest` Model (Lines 227-229):** `content`, `context_item_ids?`

**Ideas Models (Lines 232-321):**
- **`IdeaCandidateStatus` Enum (Lines 235-237):** `ACTIVE`, `ARCHIVED`
- **`IdeaCandidate` Model (Lines 240-250):**
  - Required: `id`, `project_id`, `type: str`, `summary`, `status: IdeaCandidateStatus`, `confidence: float (ge=0.0, le=1.0)`, `created_at`
  - Optional: `source_log_ids: List[str]`, `source_channel`, `source_user`
- **`IdeaCluster` Model (Lines 253-262):**
  - Required: `id`, `project_id`, `label`, `created_at`, `updated_at`
  - Optional: `description`, `color`, `idea_ids: List[str]`, `priority`
- **`IdeaTicketStatus` Enum (Lines 265-268):** `ACTIVE`, `COMPLETE`, `BLOCKED`
- **`IdeaTicketPriority` Enum (Lines 271-274):** `LOW`, `MEDIUM`, `HIGH`
- **`IdeaTicket` Model (Lines 277-293):**
  - Required: `id`, `project_id`, `title`, `status: IdeaTicketStatus`, `priority: IdeaTicketPriority`, `created_at`, `updated_at`
  - Optional: `idea_id`, `description`, `origin_story`, `category`, `implied_task_summaries: List[str]`, `repo_hints: List[str]`, `source_quotes`, `source_channel`, `confidence: float (ge=0.0, le=1.0)`
- **`MissionControlTaskColumn` Enum (Lines 296-300):** `BACKLOG`, `TODO`, `IN_PROGRESS`, `DONE`
- **`MissionControlTaskOrigin` Enum (Lines 303-306):** `REPO`, `CHAT`, `PDF`
- **`MissionControlTask` Model (Lines 309-321):**
  - Required: `id`, `project_id`, `title`, `origin: MissionControlTaskOrigin`, `confidence: float (ge=0.0, le=1.0)`, `column: MissionControlTaskColumn`, `created_at`, `updated_at`
  - Optional: `context: List[ContextItem]`, `priority`, `idea_id`, `ticket_id`

**Roadmap Models (Lines 324-376):**
- **`RoadmapNodeStatus` Enum (Lines 327-331):** `PENDING`, `ACTIVE`, `COMPLETE`, `BLOCKED`
- **`RoadmapNodePriority` Enum (Lines 334-337):** `LOW`, `MEDIUM`, `HIGH`
- **`RoadmapNode` Model (Lines 340-355):**
  - Required: `id`, `project_id`, `label`, `status: RoadmapNodeStatus`, `created_at`, `updated_at`
  - Optional: `description`, `priority: RoadmapNodePriority`, `start_date`, `target_date`, `depends_on_ids: List[str]`, `lane_id`, `idea_id`, `ticket_id`, `mission_control_task_id`
- **`RoadmapEdgeKind` Enum (Lines 358-360):** `DEPENDS_ON`, `RELATES_TO`
- **`RoadmapEdge` Model (Lines 363-370):** `id`, `project_id`, `from_node_id`, `to_node_id`, `kind: RoadmapEdgeKind`, `label?`, `created_at`
- **`RoadmapGraph` Model (Lines 373-376):** `nodes: List[RoadmapNode]`, `edges: List[RoadmapEdge]`, `generated_at: datetime`

**Knowledge Graph Models (Lines 379-426):**
- **`KnowledgeNode` Model (Lines 382-392):**
  - Required: `id`, `project_id`, `title`, `type: str`
  - Optional: `summary`, `text`, `tags: List[str]`, `metadata: dict`, `created_at`, `updated_at`
- **`KnowledgeEdge` Model (Lines 395-403):** `id`, `project_id`, `source`, `target`, `type: str`, `weight?`, `label?`, `created_at?`
- **`KnowledgeGraph` Model (Lines 406-409):** `nodes: List[KnowledgeNode]`, `edges: List[KnowledgeEdge]`, `generated_at: datetime`
- **`KnowledgeSearchRequest` Model (Lines 412-426):**
  - Required: `query: str`
  - Optional: `type?`, `tags: List[str]?`, `limit: int = 10 (ge=1, le=100)`, `max_results: int = 10 (ge=1, le=100)`, `use_vector_search: bool = True`
  - **Special Logic:** Supports both `limit` and `max_results` aliases, syncs values in `__init__` (lines 420-425)

**Streaming Event Models (Lines 429-474):**
- **`IngestJobEventType` Enum (Lines 439-443):** `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`
- **`IngestJobEvent` Model (Lines 446-448):** `event_type: IngestJobEventType`, `job: IngestJob`
- **`AgentRunEventType` Enum (Lines 451-455):** `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`
- **`AgentRunEvent` Model (Lines 458-460):** `event_type: AgentRunEventType`, `run: AgentRun`
- **`WorkflowNodeEventType` Enum (Lines 463-467):** `NODE_STARTED`, `NODE_PROGRESS`, `NODE_COMPLETED`, `NODE_FAILED`
- **`WorkflowNodeEvent` Model (Lines 470-473):** `event_type: WorkflowNodeEventType`, `run_id`, `node_id`, `state: WorkflowNodeState`

**Utility Models:**
- **`MessageResponse` Model (Lines 432-433):** `message: str` - Simple text response for stubs

**Design Patterns:**
- **Enum Usage:** All status/type fields use string-based Enums for JSON serialization
- **Field Validation:** Extensive use of `Field(ge=..., le=...)` for numeric constraints
- **Default Factories:** Lists use `Field(default_factory=list)` to avoid mutable default arguments
- **Optional Fields:** Extensive use of `Optional[...]` for backward compatibility
- **CamelCase Aliases:** Project models use `to_camel` alias generator for API consistency
- **Type Safety:** Strong typing throughout with Pydantic validation

---

## LangGraph Integration Analysis

LangGraph integration (`backend/app/graphs/` and `backend/app/tools/`) provides agent orchestration and tool execution capabilities.

### ProjectManagerGraph (`backend/app/graphs/project_manager_graph.py`)

**AgentState TypedDict (Lines 51-55):** Defines state structure for LangGraph execution:
- `messages: Sequence[BaseMessage]` - conversation history
- `project_id: str` - current project context
- `generated_artifacts: List[str]` - artifacts created during execution

**LLM Configuration (Lines 58-65):** Configures `ChatOpenAI` client:
- Uses `settings.llm_model_name` from config (line 60)
- Sets `temperature=0` for deterministic behavior (line 61)
- Enables streaming (line 62)
- Configures base_url and api_key from settings (lines 63-64)
- Binds tools to model (line 66)

**Tools Array (Line 31):** Defines three LangChain tools:
- `search_knowledge(query)` - searches RAG service
- `create_roadmap(intent, project_id)` - creates roadmap nodes
- `trigger_n8n_workflow(workflow_id, payload)` - triggers external workflow

**Tool Executor (Lines 34-48):** Creates `ToolExecutor` with fallback:
- Uses LangChain's `ToolExecutor` if available (line 35)
- Falls back to `SimpleToolExecutor` if import fails (lines 38-47)
- `SimpleToolExecutor` provides basic tool invocation via name lookup

**Project Manager Agent Node (Lines 69-77):** `project_manager_agent(state)` is the main agent node:
- Prepends project_id context to messages (line 74)
- Invokes model with messages (line 76)
- Returns updated messages list (line 77)

**Tool Execution Node (Lines 80-92):** `tool_execution_node(state)` executes tool calls:
- Extracts tool_calls from last message (line 83)
- Injects project_id into `create_roadmap` tool args (lines 88-89)
- Executes each tool via `tool_executor.invoke` (line 90)
- Returns `ToolMessage` responses (line 91)

**Conditional Edge Logic (Lines 95-99):** `should_continue(state)` determines graph flow:
- Returns "tools" if last message has tool_calls (line 98)
- Returns `END` otherwise (line 99)

**Graph Construction (Lines 102-116):** Builds LangGraph `StateGraph`:
- Adds "agent" node (line 104)
- Adds "tools" node (line 105)
- Sets "agent" as entry point (line 107)
- Adds conditional edge from "agent" (lines 109-112)
- Adds edge from "tools" back to "agent" (line 114)
- Compiles graph to executable app (line 116)

**Graph Flow:** Agent → (has tool_calls?) → Tools → Agent → END

### N8N Tool Integration (`backend/app/tools/n8n.py`)

**Tool Definition (Lines 9-15):** `trigger_n8n_workflow(workflow_id, payload)` is async LangChain tool:
- Constructs webhook URL from workflow_id (line 12)
- Makes POST request with payload (line 14)
- Returns status message (line 15)
- Uses `httpx.AsyncClient` for async HTTP (line 13)

**Tool Decorator:** Uses `@tool` decorator from LangChain (lines 3-6 with fallback import).

**Design Note:** Tool is async but LangGraph execution may be sync. Verify async/sync compatibility in execution context.

### WorkflowGraphCompiler (`backend/app/services/workflow_compiler.py`)

**WorkflowState TypedDict (Lines 13-22):** Defines state for workflow execution:
- `run_id: str` - workflow run identifier
- `project_id: str` - project context
- `input: Dict[str, Any]` - workflow input data
- `output: Dict[str, Any]` - accumulated output
- `messages: list` - execution messages
- `current_node: Optional[str]` - active node ID

**Compiler Class (Lines 24-65):** `WorkflowGraphCompiler` compiles `WorkflowGraph` to LangGraph `StateGraph`.

**Compile Method (Lines 27-52):** `compile(workflow_graph)` builds LangGraph:
- Creates `StateGraph(WorkflowState)` (line 29)
- Adds node for each workflow node (lines 32-33)
- Processes edges to find entry/exit points (lines 37-43)
- Sets entry point from `__start__` edge or first node (lines 46-50)
- Returns compiled graph (line 52)

**Node Function Factory (Lines 54-65):** `_create_node_function(node)` creates executable function:
- Returns async function that updates state (lines 57-63)
- Logs node execution (line 60)
- Updates output dict with node results (line 63)
- Sets `current_node` in state (line 63)

**Placeholder Implementation:** Node functions are placeholders; actual execution logic handled by `WorkflowService` during runtime.

**Integration Point:** `WorkflowService.execute_workflow_run` uses compiler to create executable graph, then invokes with initial state.

---

## Frontend Architecture Analysis

Frontend architecture (`frontend/src/`) implements React-based UI with TypeScript, using React Query for data fetching and Zustand for global state.

### Application Structure

**Directory Layout:**
- `components/` - React UI components
- `hooks/` - Custom React hooks for data fetching
- `lib/` - Utility functions (HTTP client, API client, error handling)
- `domain/` - TypeScript type definitions
- `state/` - Zustand store definitions
- `providers/` - React context providers

### Core HTTP Client (`frontend/src/lib/http.ts`)

**Base URL Configuration (Lines 52-60):** Configurable API base URL:
- Defaults to `VITE_CORTEX_API_BASE_URL` or `http://localhost:8000` (line 53)
- `setApiBaseUrl(url)` allows runtime override (lines 66-68)

**Auth Token Provider (Lines 55-60):** Configurable token retrieval:
- Default provider reads from `localStorage.getItem("cortex_auth_token")` (line 59)
- `setAuthTokenProvider(provider)` allows custom provider (lines 74-76)

**URL Builder (Lines 78-91):** `buildUrl(path, query)` constructs full URL:
- Normalizes base URL and path (lines 79-80)
- Appends query parameters (lines 84-87)
- Handles null/undefined values (line 85)

**JSON Parser (Lines 93-102):** `parseJsonSafe(response)` safely parses JSON:
- Checks Content-Type header (line 94)
- Returns `undefined` if not JSON or parse fails (lines 95, 100)

**Core HTTP Function (Lines 110-165):** `http<TResponse>(path, options)` is main HTTP client:
- Builds URL with query params (line 116)
- Sets Accept and Content-Type headers (lines 118-125)
- Injects Authorization header if token available (lines 127-130)
- Handles FormData vs JSON body (lines 138-140)
- Throws `ApiError` on non-2xx responses (lines 144-156)
- Returns parsed JSON or undefined for 204 No Content (lines 158-164)

**ApiError Class (Lines 37-49):** Custom error class for API failures:
- Extends `Error` with status, code, details fields
- Used for error handling and retry logic

### API Client (`frontend/src/lib/cortexApi.ts`)

**Typed API Functions:** All functions use generic type parameters for response types:
- `getProjects(): Promise<CortexProject[]>` (line 15)
- `getProject(projectId): Promise<CortexProject>` (line 22)
- `createProject(payload): Promise<CortexProject>` (line 29)
- Similar patterns for all resources

**Project Endpoints (Lines 14-50):** CRUD operations for projects:
- List, get, create, update, delete
- Uses `/api/projects` base path

**Ingest Endpoints (Lines 52-120):** Job management:
- `listIngestJobs(projectId, params)` with filtering (line 55)
- `getIngestJob(projectId, jobId)` (line 62)
- `createIngestJob(projectId, request)` (line 69)
- `cancelIngestJob(projectId, jobId)` (line 76)
- `deleteIngestJob(projectId, jobId)` (line 83)
- `uploadFile(projectId, file)` uses FormData (line 90)

**Agent Run Endpoints (Lines 122-220):** Agent execution:
- `listAgentRuns(projectId, params)` (line 125)
- `getAgentRun(projectId, runId)` (line 132)
- `startAgentRun(projectId, payload)` (line 139)
- `cancelAgentRun(projectId, runId)` (line 146)
- `listAgentRunSteps(projectId, runId, params)` (line 153)
- `listAgentRunMessages(projectId, runId, params)` (line 160)
- `appendAgentRunMessage(projectId, runId, payload)` (line 167)
- `listAgentRunNodeStates(projectId, runId)` (line 174)

**Workflow Endpoints (Lines 222-290):** Workflow management:
- `listWorkflowGraphs(projectId)` (line 225)
- `getWorkflowGraph(projectId, workflowId)` (line 232)
- `createWorkflowGraph(projectId, payload)` (line 239)
- `listWorkflowRuns(projectId, params)` (line 246)
- `createWorkflowRun(projectId, payload)` (line 253)
- `getWorkflowRun(projectId, runId)` (line 260)
- `executeWorkflowRun(projectId, runId, payload)` (line 267)
- `cancelWorkflowRun(projectId, runId)` (line 274)
- `pauseWorkflowRun(projectId, runId, payload)` (line 281)
- `resumeWorkflowRun(projectId, runId)` (line 288)

**Roadmap Endpoints (Lines 292-370):** Roadmap graph operations:
- `fetchRoadmap(projectId)` (line 295)
- `listRoadmapNodes(projectId, params)` (line 302)
- `createRoadmapNode(projectId, payload)` (line 309)
- `getRoadmapNode(projectId, nodeId)` (line 316)
- `updateRoadmapNode(projectId, nodeId, payload)` (line 323)
- `deleteRoadmapNode(projectId, nodeId)` (line 330)
- `createRoadmapEdge(projectId, payload)` (line 337)
- `deleteRoadmapEdge(projectId, edgeId)` (line 344)

**Knowledge Graph Endpoints (Lines 372-470):** Knowledge graph operations:
- `fetchKnowledgeGraph(projectId, options)` (line 375)
- `getKnowledgeNode(projectId, nodeId)` (line 382)
- `getKnowledgeNodeNeighbors(projectId, nodeId)` (line 389)
- `createKnowledgeNode(projectId, payload)` (line 396)
- `updateKnowledgeNode(projectId, nodeId, payload)` (line 403)
- `createKnowledgeEdge(projectId, payload)` (line 410)
- `deleteKnowledgeEdge(projectId, edgeId)` (line 417)
- `searchKnowledge(projectId, query, params)` (line 600)

**Context Endpoints (Lines 618-668):** Context management:
- `getContext(projectId)` (line 619)
- `addContextItems(projectId, payload)` (line 628)
- `updateContextItem(projectId, itemId, payload)` (line 643)
- `removeContextItem(projectId, itemId)` (line 658)

**All Functions:** Use `http<T>()` utility with typed responses. Path encoding via `encodeURIComponent` for IDs. Consistent error handling via `ApiError`.

### Error Handling (`frontend/src/lib/errorHandling.ts`)

**Get Error Message (Lines 10-46):** `getErrorMessage(error)` extracts user-friendly message:
- Maps HTTP status codes to messages (lines 13-34)
- Handles `ApiError`, `Error`, string, unknown types
- Returns generic message for unknown errors (line 45)

**Get Error Code (Lines 51-56):** `getErrorCode(error)` extracts error code from `ApiError`.

**Is Retryable Error (Lines 61-67):** `isRetryableError(error)` determines if error should be retried:
- Returns true for 5xx errors and 429 Too Many Requests (line 64)

**Log Error (Lines 72-86):** `logError(error, context)` logs errors with context:
- Extracts message and code (lines 73-74)
- Logs to console with timestamp (lines 76-82)
- Placeholder for error tracking service integration (line 85)

**Categorize Error (Lines 103-118):** `categorizeError(error)` classifies error type:
- Returns "network", "validation", "authentication", "authorization", "not_found", "server", "unknown"
- Uses status code ranges and error message patterns

### State Management (`frontend/src/state/cortexStore.ts`)

**Zustand Store (Lines 5-28):** `CortexStoreState` interface defines store shape:
- `currentProjectId: string | null` - selected project
- `projects: CortexProject[]` - cached project list
- `setCurrentProjectId(projectId)` - update selection
- `setProjects(projects)` - update cache
- `upsertProject(project)` - add or update single project

**Store Implementation (Lines 13-28):** `useCortexStore` created with `create()`:
- Initial state: `currentProjectId: null`, `projects: []` (lines 14-15)
- `setCurrentProjectId` updates selection (line 16)
- `setProjects` replaces entire list (line 17)
- `upsertProject` finds existing or appends (lines 18-27)

**Design Note:** Store acts as cache; React Query is source of truth. Store synced via hooks.

### Custom Hooks Analysis

**useProjects (`frontend/src/hooks/useProjects.ts`):**
- `useProjects()` fetches all projects, syncs to store (lines 16-34)
- `useCurrentProject()` returns selected project from store + query data (lines 40-60)
- Uses `projectsQueryKey` for React Query cache key (line 7)

**useIngestJobs (`frontend/src/hooks/useIngestJobs.ts`):**
- `useIngestJobs(projectId, params)` lists jobs with filtering (lines 31-47)
- `useIngestJob(projectId, jobId)` fetches single job (lines 52-65)
- `useCreateIngestJob`, `useCancelIngestJob`, `useDeleteIngestJob` mutations (lines 67-101)
- Mutations invalidate query cache on success (lines 72, 84, 96)

**useAgentRuns (`frontend/src/hooks/useAgentRuns.ts`):**
- Multiple query keys for different data (lines 16-29)
- `useAgentRuns`, `useAgentRun`, `useAgentRunSteps`, `useAgentRunMessages`, `useAgentRunNodeStates` queries
- `useStartAgentRun`, `useCancelAgentRun`, `useAppendAgentRunMessage` mutations
- Mutations invalidate related queries (lines 66, 82, 126)

**useRoadmap (`frontend/src/hooks/useRoadmap.ts`):**
- `useRoadmap(projectId)` fetches complete graph (lines 39-55)
- `useRoadmapNodes(projectId, options)` lists nodes with filtering (lines 60-79)
- CRUD mutations for nodes and edges (lines 84-158)
- Mutations invalidate graph and nodes queries (lines 89, 106, 122, 138, 153)

**useKnowledgeGraph (`frontend/src/hooks/useKnowledgeGraph.ts`):**
- `useKnowledgeGraph(projectId, options)` fetches graph with view/focus filters (lines 40-53)
- `useKnowledgeNode`, `useKnowledgeNodeNeighbors` queries (lines 58-94)
- CRUD mutations for nodes and edges (lines 100-165)
- `useSearchKnowledge` mutation for search (lines 170-181)
- Mutations invalidate graph and neighbor queries (lines 105, 121, 138, 159, 176)

**useContextItems (`frontend/src/hooks/useContextItems.ts`):**
- `useContextBudget(projectId)` fetches budget (lines 14-27)
- `useAddContextItems`, `useUpdateContextItem`, `useRemoveContextItem` mutations (lines 29-64)
- All mutations invalidate context query (lines 34, 47, 59)

**useIdeas (`frontend/src/hooks/useIdeas.ts`):**
- `useIdeas(opts)` fetches tickets (lines 43-56)
- `useIdeaCandidates`, `useIdeaClusters`, `useIdeaTickets` queries
- CRUD mutations for candidates, clusters, tickets (lines 82-181)
- Mutations invalidate related queries (lines 87, 103, 139, 175)

**Hook Pattern:** All hooks follow consistent patterns:
- Use React Query `useQuery` for reads, `useMutation` for writes
- Define query keys as const arrays for type safety
- Enable queries conditionally based on required params (`enabled: !!projectId`)
- Mutations invalidate related queries on success
- Return `{ data, isLoading, error, refetch }` for queries
- Return mutation object with `mutate`, `isLoading`, `error` for mutations

### React Components Analysis

**ErrorBoundary (`frontend/src/components/ErrorBoundary.tsx`):**
- Class component implementing React Error Boundary (lines 21-106)
- `getDerivedStateFromError` sets error state (lines 27-29)
- `componentDidCatch` logs error via `logError` (lines 31-38)
- Renders fallback UI with error message and stack trace (dev only) (lines 51-101)
- Provides reset and reload buttons (lines 85-97)

**ErrorDisplay (`frontend/src/components/ErrorDisplay.tsx`):**
- Functional component for displaying API errors (lines 18-98)
- Uses `getErrorMessage`, `categorizeError`, `isRetryableError` utilities
- Color-codes errors by type (network=red, auth=yellow, validation=orange)
- Shows retry button if error is retryable (lines 76-84)
- Dismiss button if `onDismiss` provided (lines 85-93)

**ToastContainer (`frontend/src/components/ToastContainer.tsx`):**
- Renders toast notifications with `framer-motion` animations (lines 15-79)
- Maps toast types to icons (success=CheckCircle, error=AlertCircle, etc.) (lines 16-27)
- Color-codes backgrounds by type (lines 29-40)
- Animates enter/exit with slide and fade (lines 46-51)
- Fixed position top-right with z-index 50 (line 43)

**AppProviders (`frontend/src/providers/AppProviders.tsx`):**
- Root provider component wrapping app (lines 53-68)
- Creates `QueryClient` with retry and error handling config (lines 13-35)
- Wraps children with `ErrorBoundary`, `QueryClientProvider`, `ToastProvider` (lines 55-65)
- Configures React Query defaults:
  - Retries 3 times for network/server errors, not for 4xx (lines 16-22)
  - Exponential backoff retry delay (line 24)
  - Error logging on queries and mutations (lines 25-32)

**ToastProvider (Lines 37-51):** Manages toast state via `useToast` hook:
- Exposes toast to window object for global access (lines 41-43)
- Renders `ToastContainer` with toasts and dismiss handler (line 48)

### Domain Types (`frontend/src/domain/types.ts`)

**Type Definitions:** Comprehensive TypeScript interfaces mirroring backend Pydantic models:
- `ID` type alias for string (line 8)
- `CortexProject` with all project fields (lines 10-30)
- `IngestJob`, `AgentRun`, `AgentStep`, `AgentMessage`, `AgentNodeState` (lines 32-150)
- `RoadmapNode`, `RoadmapEdge`, `RoadmapGraph` (lines 152-200)
- `KnowledgeNode`, `KnowledgeEdge`, `KnowledgeGraph` (lines 200-250)
- `IdeaCandidate`, `IdeaCluster`, `IdeaTicket` (lines 252-350)
- `ContextItem`, `ContextBudget` (lines 352-400)
- `MissionControlTask` (lines 400-450)

**Enum Types:** String literal unions for statuses, priorities, types:
- `AgentRunStatus`, `AgentStepStatus`, `AgentNodeStatus`
- `RoadmapNodeStatus`, `RoadmapPriority`
- `IdeaTicketStatus`, `IdeaTicketPriority`
- `ContextItemType`

**API Types (`frontend/src/domain/api-types.ts`):** Request/response types for API calls:
- `PaginatedResponse<T>` generic type (lines 13-17)
- Request types for create/update operations
- Response types matching backend models
- WebSocket event types (lines 451-477)

**Type Safety:** All API functions use generic type parameters. Frontend types align with backend Pydantic models via shared domain definitions.

---

## Testing Infrastructure Analysis

Testing infrastructure spans backend pytest tests and frontend E2E Playwright tests.

### Backend Test Structure (`backend/tests/`)

**Conftest (`backend/tests/conftest.py`):**
- `client` fixture: Session-scoped `TestClient` for FastAPI app (lines 13-23)
- Deletes test database before each session (lines 17-19)
- `project` fixture: Creates test project per test (lines 26-44)
- Returns project dict with `id` and `name` (line 43)

**Test Projects (`backend/tests/test_projects.py`):**
- `test_list_projects_initial`: Verifies empty list returns (lines 5-20)
- `test_create_project_and_list_again`: Creates project, verifies it appears in list (lines 22-44)
- Uses `TestClient` for HTTP calls
- Asserts status codes and response structure

**Test Agents API (`backend/tests/test_agents_api.py`):**
- Tests all agent run endpoints (lines 9-118)
- Creates runs, verifies steps/messages/node states
- Tests cancellation and message appending
- Uses `project` fixture for project-scoped resources

**Test Workflows API (`backend/tests/test_workflows_api.py`):**
- Tests workflow graph and run endpoints (lines 9-93)
- Creates runs, verifies execution and cancellation
- Tests status endpoint
- Handles optional workflow graph existence

**Test Context API (`backend/tests/test_context_api.py`):**
- Tests context budget and item operations (lines 9-83)
- Verifies budget calculations
- Tests add/update/remove item flows
- Asserts budget updates correctly

**Test Ingest (`backend/tests/test_ingest.py`):**
- Tests ingest job creation and listing (lines 5-98)
- Adapts to current API structure (noted mismatch with api-contract.md)
- Verifies job appears in list after creation
- Tests status and stage fields

**Test Gap Analysis Service (`backend/tests/test_gap_analysis_service.py`):**
- Uses fake dependencies (ticket provider, code search, LLM client) (lines 14-42)
- Tests unmapped, implemented, partially_implemented scenarios (lines 45-141)
- Verifies status classification logic
- Tests confidence score calculations

**Test Gap Analysis API (`backend/tests/test_gap_analysis_api.py`):**
- Uses `app_with_gap_api` fixture with fake dependencies (lines 72-104)
- Tests `run_gap_analysis`, `get_latest_gap_analysis`, `list_gap_analysis_history` endpoints
- Verifies report generation and persistence
- Tests history ordering (newest-first)

**Test Mode API (`backend/tests/test_mode_api.py`):**
- Tests project execution settings endpoints (lines 22-101)
- Verifies default settings creation
- Tests partial updates (PATCH)
- Resets in-memory store between tests (lines 15-19)

**Test System Metrics (`backend/tests/test_system_metrics.py`):**
- Uses monkeypatching to inject fake metrics (lines 32-152)
- Tests nominal, warning, critical status classification
- Verifies GPU metrics parsing and graceful degradation
- Tests CPU, memory, GPU, context threshold logic

**Test Graphs (`backend/tests/test_graphs.py`):**
- Tests roadmap and knowledge graph endpoints (lines 5-84)
- Adapts to available endpoints (noted implementation differences)
- Verifies graph structure (nodes, edges arrays)
- Tests node/edge field validation

**Test Mode Integration (`backend/tests/test_mode_integration.py`):**
- Tests `llm_service.generate_text` with mode settings (lines 63-111)
- Verifies temperature override from project settings
- Tests paranoid mode validation passes (expects 3 LLM calls: 1 primary + 2 checker)
- Uses dummy LLM with call tracking

### E2E Test Structure (`e2e/`)

**Fixtures (`e2e/fixtures.ts`):**
- `api` fixture: `APIRequestContext` for direct API calls (lines 17-21)
- `authenticatedPage` fixture: Stubbed for now (lines 23-28)
- `testProject` fixture: Creates project per test, cleans up after (lines 30-49)
- Uses `expect` from Playwright (line 52)

**API Helpers (`e2e/utils/api-helpers.ts`):**
- `ApiHelpers` class wraps common API operations (lines 5-119)
- Methods: `createProject`, `deleteProject`, `createIngestJob`, `getIngestJobs`, `createAgentRun`, `getAgentRun`, `createRoadmapNode`, `getRoadmapNodes`, `addContextItems`, `getContext`, `createKnowledgeNode`, `searchKnowledge`
- Throws errors with status codes for debugging
- Re-exports `expect` for convenience (line 121)

**Test Data Factory (`e2e/utils/test-data-factory.ts`):**
- `TestDataFactory` static methods generate consistent test data (lines 7-66)
- Methods: `generateProject`, `generateIngestJob`, `generateAgentRun`, `generateRoadmapNode`, `generateContextItem`, `generateKnowledgeNode`
- Uses `Date.now()` for unique identifiers
- Provides sensible defaults with override support

**WebSocket Client (`e2e/utils/websocket-client.ts`):**
- `WebSocketTestClient` class for WebSocket testing (lines 13-185)
- Methods: `connect()`, `send()`, `subscribe()`, `waitForEvent()`, `getEventsByType()`, `getAllEvents()`, `clearEvents()`, `disconnect()`
- Tracks event history internally
- Auto-reconnect logic (lines 80-88)
- `createWebSocketClient` helper for Playwright context (lines 190-203)

**Projects Spec (`e2e/projects.spec.ts`):**
- Tests project CRUD operations (lines 4-49)
- Creates, lists, gets projects
- Uses `ApiHelpers` for API calls
- Cleans up created projects

**Ingest Spec (`e2e/ingest.spec.ts`):**
- Tests ingest job lifecycle (lines 4-90)
- Creates, lists, gets, cancels, deletes jobs
- Verifies job appears in list after creation
- Tests cancellation and deletion flows

**Agent Runs Spec (`e2e/agent-runs.spec.ts`):**
- Tests agent run operations (lines 4-125)
- Creates runs, gets steps/messages/node states
- Tests cancellation
- Verifies run appears in list

**Roadmap Spec (`e2e/roadmap.spec.ts`):**
- Tests roadmap node and edge operations (lines 4-124)
- Creates nodes, lists, gets, updates, deletes
- Creates edges between nodes
- Verifies graph structure

**Knowledge Spec (`e2e/knowledge.spec.ts`):**
- Tests knowledge graph operations (lines 4-137)
- Creates nodes, gets graph, searches, updates
- Creates edges
- Tests search functionality

**Context Spec (`e2e/context.spec.ts`):**
- Tests context management (lines 4-117)
- Gets budget, adds/updates/removes items
- Tests budget overflow prevention
- Verifies budget calculations

**WebSocket Spec (`e2e/websocket.spec.ts`):**
- Basic WebSocket connection tests (lines 9-59)
- Tests endpoint existence
- Verifies event triggers for ingest jobs and agent runs
- Notes limitations of Playwright WebSocket support

**Playwright Config (`playwright.config.ts`):**
- Configures parallel execution, retries, reporters (lines 6-17)
- Sets base URL, trace collection, screenshots (lines 19-30)
- Visual comparison thresholds (lines 32-43)
- Browser projects: chromium, firefox, webkit, mobile (lines 45-77)
- Web server commands for backend and frontend (lines 80-101)
- Backend: uvicorn on port 8000 with test env vars
- Frontend: pnpm dev on port 5173

---

## Configuration and Deployment Analysis

Configuration spans environment variables, Nix flakes, Docker Compose, and deployment scripts.

### Environment Configuration (`backend/app/config.py`)

**Settings Model:** Pydantic `Settings` class with environment variable loading:
- `atlas_db_path`: SQLite database path (default: `./atlas.db`)
- `qdrant_url`: Qdrant vector DB URL (default: `http://localhost:6333`)
- `llm_base_url`: LLM API base URL
- `llm_api_key`: LLM API key
- `llm_model_name`: Model identifier
- `normal_mode_llm_temperature`: Default temperature for normal mode
- `paranoid_mode_llm_temperature`: Temperature for paranoid mode
- `normal_mode_validation_passes`: Validation passes for normal mode (default: 1)
- `paranoid_mode_validation_passes`: Validation passes for paranoid mode (default: 3)
- `normal_mode_max_parallel_tools`: Max parallel tools for normal mode (default: 8)
- `paranoid_mode_max_parallel_tools`: Max parallel tools for paranoid mode (default: 2)

**Settings Singleton:** `get_settings()` uses `lru_cache` for singleton access (line 15).

### Docker Compose (`ops/docker-compose.yml`)

**Qdrant Service (Lines 4-10):**
- Image: `qdrant/qdrant:latest`
- Ports: 6333 (HTTP), 6334 (gRPC)
- Volume: `./qdrant_storage:/qdrant/storage` for persistence

**Inference Engine Service (Lines 11-21):**
- Builds from `Dockerfile.vllm` (not present in codebase)
- Maps ROCm devices (`/dev/kfd`, `/dev/dri`)
- Port: 11434 → 8000 (OpenAI-compatible API)
- Shared memory: 16GB for model loading
- Volume: `./models:/root/.cache/huggingface` for model cache

**Design Note:** vLLM service configured for AMD ROCm hardware. Requires ROCm drivers and compatible GPU.

### Deployment Script (`deploy.sh`)

**Script Flow (Lines 1-56):**
1. Checks nix-shell environment (lines 11-15)
2. Installs backend dependencies via Poetry (lines 17-20)
3. Installs frontend dependencies via pnpm (lines 23-27)
4. Installs root dependencies (lines 30-33)
5. Starts Docker services (lines 36-38)
6. Installs Playwright browsers (lines 41-43)
7. Prints service URLs and commands (lines 46-55)

**Error Handling:** Uses `set -e` for fail-fast behavior (line 6).

**Service URLs:**
- Qdrant: `http://localhost:6333`
- Backend: `http://localhost:8000` (manual start)
- Frontend: `http://localhost:5173` (manual start)

### Nix Configuration

**Traditional Shell (`shell.nix`):**
- Provides Python 3.11, Poetry, Node.js 20, pnpm, TypeScript, Playwright
- Includes Playwright system dependencies (alsa-lib, nss, gtk3, etc.)
- Sets environment variables in shellHook (lines 92-107)
- LD_LIBRARY_PATH for Playwright browsers (line 111)

**Flake (`flake.nix`):**
- Defines development shell with all tools (lines 112-151)
- Imports backend and frontend sub-flakes (lines 81-88)
- Creates `cortex-docker` wrapper script for docker-compose (lines 91-108)
- Packages: backend, frontend, docker-compose wrapper (lines 154-166)
- Formatter: nixpkgs-fmt (line 169)

**Flake Inputs:**
- `nixpkgs`: nixos-unstable
- `flake-utils`: For system-specific outputs
- `poetry2nix`: For Python dependency management

### Frontend Configuration

**Vite Config (`frontend/vite.config.ts`):**
- Dev server: port 3000, host 0.0.0.0 (lines 8-11)
- React plugin (line 12)
- Environment variables: `GEMINI_API_KEY` (lines 14-15)
- Path alias: `@` → project root (lines 18-20)

**TypeScript Config (`frontend/tsconfig.json`):**
- Target: ES2022
- Module: ESNext
- JSX: react-jsx
- Strict mode enabled
- Path aliases: `@/*` → `./*`

**Package.json (`frontend/package.json`):**
- Dependencies: React 19.2.0, React DOM 19.2.0, @tanstack/react-query 5.50.1, zustand 4.5.4, lucide-react, clsx, react-force-graph-2d, reactflow 11.10.1, framer-motion 11.0.8, date-fns 3.3.1
- Dev dependencies: @types/node, @vitejs/plugin-react, TypeScript 5.8.2, Vite 6.2.0

### Backend Configuration

**Pyproject.toml (`pyproject.toml`):**
- Poetry project: `cortex-monorepo` version 0.1.0
- Python: ^3.11
- Ruff config: line-length 120, target-version py311
- MyPy config: python_version 3.11, pydantic plugin

**Database Path:** Configurable via `CORTEX_ATLAS_DB_PATH` environment variable, defaults to `./atlas.db`.

**Qdrant URL:** Configurable via `CORTEX_QDRANT_URL`, defaults to `http://localhost:6333`.

**LLM Configuration:** All LLM settings via environment variables (`CORTEX_LLM_BASE_URL`, `CORTEX_LLM_API_KEY`, `CORTEX_LLM_MODEL_NAME`).

---

## External Integrations Analysis

External integrations include Qdrant vector database, LLM services, LangGraph, n8n, and streaming infrastructure.

### Qdrant Integration

**QdrantService (`backend/app/services/qdrant_service.py`):**
- Initializes `QdrantClient` with configurable URL (lines 32-43)
- Falls back gracefully if Qdrant unavailable (line 42)
- Initializes `SentenceTransformer` model "all-MiniLM-L6-v2" (384 dimensions) (lines 45-52)
- Collection naming: `{collection_type}_{project_id}` (line 56)
- `ensure_collection()` creates collections with COSINE distance (lines 58-75)
- `generate_embedding(text)` encodes text to vector (lines 77-85)
- `upsert_knowledge_node()` stores node with embedding (lines 87-132)
- `delete_knowledge_node()` removes node from Qdrant (lines 134-146)
- `search_knowledge_nodes()` performs vector similarity search (lines 148-203)
- `hybrid_search()` placeholder for keyword + vector search (lines 205-222)

**QdrantCodeSearchBackend (`backend/app/services/qdrant_code_search.py`):**
- Uses code-specific embedding model: `jinaai/jina-embeddings-v2-base-code` (768 dims) or fallback `microsoft/codebert-base` (768 dims) or `all-MiniLM-L6-v2` (384 dims) (lines 46-59)
- Collection: `cortex_codebase` (line 36)
- `_chunk_code_ast()` attempts AST-aware chunking with tree-sitter (lines 76-109)
- `_chunk_code_simple()` falls back to function/class-based chunking (lines 111-168)
- `search_related_code()` performs vector search with project filter (lines 170-213)
- `ingest_code_file()` chunks and indexes code files (lines 215-255)

**Design Notes:**
- Qdrant connection failures are handled gracefully (services continue without vector search)
- Embedding models loaded on service initialization (memory overhead)
- Code chunking supports AST-aware and simple modes
- Project-scoped collections enable multi-tenancy

### LLM Service Integration

**LLMService (`backend/app/services/llm_service.py`):**
- Uses `openai.OpenAI` client with configurable base_url and api_key (line 16)
- `generate_text()` applies project-specific execution settings (lines 42-113)
- Reads project settings via `get_project_settings()` (line 55)
- Applies temperature override from project settings (line 58)
- Normal mode: single LLM call, returns raw response (lines 82-83)
- Paranoid mode: primary call + N validation passes (lines 85-112)
- Validation passes use checker prompt with lower temperature (line 107)
- Logs all LLM calls with project_id, mode, temperature, model (lines 60-69, 96-103)

**Design Notes:**
- LLM service abstracts underlying provider (OpenAI-compatible API)
- Project-specific settings allow per-project behavior tuning
- Paranoid mode adds latency but increases reliability
- All LLM calls logged for observability

### LangGraph Integration

**ProjectManagerGraph (`backend/app/graphs/project_manager_graph.py`):**
- Defines agent workflow with "agent" and "tools" nodes
- Conditional edge logic routes based on tool_calls presence
- Tools: `search_knowledge`, `create_roadmap`, `trigger_n8n_workflow`
- State includes messages, project_id, generated_artifacts

**WorkflowGraphCompiler (`backend/app/services/workflow_compiler.py`):**
- Compiles `WorkflowGraph` domain model to LangGraph `StateGraph`
- Creates node functions for each workflow node
- Handles entry/exit points via `__start__` and `__end__` edges
- Placeholder node functions; actual execution in `WorkflowService`

**AgentService Integration (`backend/app/services/agent_service.py`):**
- `execute_run()` uses `project_manager_graph.app` (line 504)
- Invokes graph with initial state containing messages and project_id (line 504)
- Updates run status and node states during execution
- Emits streaming events via `streaming_service`

**Design Notes:**
- LangGraph provides deterministic agent execution
- State persisted in database via `AgentRun`, `AgentStep`, `AgentNodeState`
- Graph compilation happens at runtime (could be cached)
- Tool execution integrated with project context

### N8N Integration

**N8N Tool (`backend/app/tools/n8n.py`):**
- `trigger_n8n_workflow(workflow_id, payload)` async tool
- Constructs webhook URL: `http://localhost:5678/webhook/{workflow_id}`
- Makes POST request with JSON payload
- Returns status message

**Design Notes:**
- N8N runs as separate service (not in docker-compose.yml)
- Tool provides simple HTTP integration
- Could be extended for response handling, error retries

### Streaming Integration

**StreamingService (`backend/app/services/streaming_service.py`):**
- `ConnectionManager` manages WebSocket connections per project (lines 12-62)
- `active_connections: Dict[str, Set[WebSocket]]` maps project_id to websockets (line 17)
- `connect()` accepts websocket and adds to project set (lines 20-27)
- `disconnect()` removes websocket from set (lines 29-36)
- `broadcast()` sends event to all connections for project (lines 38-54)
- `send_to_connection()` sends to specific websocket (lines 56-62)
- `emit_ingest_event()`, `emit_agent_event()`, `emit_workflow_event()` helper functions (lines 69-124)
- Events include timestamp and type-specific data

**Streaming Routes (`backend/app/api/routes/streaming.py`):**
- WebSocket endpoints: `/projects/{project_id}/ingest/{job_id}`, `/projects/{project_id}/agent-runs/{run_id}`, `/projects/{project_id}/workflows/{run_id}`
- SSE endpoint: `/projects/{project_id}/ingest/{job_id}/events`
- Polling-based implementation (1 second intervals) (lines 50, 138, 210)
- Sends initial state, then polls for updates
- Closes connection on completion/failure/disconnect

**Design Notes:**
- Current implementation uses polling (not event-driven)
- Connection manager handles multiple clients per project
- Events include timestamps for ordering
- WebSocket and SSE both supported (SSE for compatibility)

**Frontend Integration:** No WebSocket client code found in frontend hooks. Frontend would need to implement WebSocket connections to consume streaming events.

---

## Database Schema Deep Dive

Complete analysis of SQLite schema in `backend/app/db.py` covering all 20+ tables, relationships, indexes, and query patterns.

### Schema Initialization

**Database Path (Lines 11-15):** `_db_path()` resolves path from settings:
- Uses `settings.atlas_db_path` (default: `./atlas.db`)
- Creates parent directories if needed (line 14)
- Returns `Path` object

**Connection Management (Lines 18-30):**
- `get_connection()` creates SQLite connection with `row_factory=sqlite3.Row` (line 20)
- `check_same_thread=False` allows multi-threaded access (line 19)
- `db_session()` context manager ensures connection cleanup (lines 24-30)

**Schema Script (Lines 33-350):** `init_db()` executes single transaction:
- Sets `PRAGMA journal_mode=WAL` for write-ahead logging (line 38)
- Creates all tables with `CREATE TABLE IF NOT EXISTS`
- Creates indexes with `CREATE INDEX IF NOT EXISTS`
- Commits transaction atomically (line 350)

### Table Definitions

**Projects Table (Lines 39-50):**
- Primary key: `id TEXT`
- Unique constraint: `slug TEXT UNIQUE`
- Fields: `name`, `description`, `status`, `created_at`, `updated_at`, `default_model_role_id`, `root_idea_cluster_id`, `roadmap_id`
- Indexes: `idx_projects_status`, `idx_projects_slug`

**Ingest Sources Table (Lines 54-64):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `kind`, `name`, `description`, `uri`, `created_at`, `updated_at`
- Index: `idx_ingest_sources_project`

**Ingest Jobs Table (Lines 67-85):**
- Primary key: `id TEXT`
- Foreign keys: `project_id` → `projects.id`, `source_id` → `ingest_sources.id`
- Fields: `original_filename`, `byte_size`, `mime_type`, `is_deep_scan`, `stage`, `progress`, `status`, `created_at`, `updated_at`, `completed_at`, `error_message`, `canonical_document_id`
- Indexes: `idx_ingest_jobs_project`, `idx_ingest_jobs_source`

**Idea Tickets Table (Lines 89-102):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `cluster_id`, `title`, `description`, `status`, `priority`, `created_at`, `updated_at`, `origin_idea_ids_json`
- Index: `idx_idea_tickets_project`

**Knowledge Nodes Table (Lines 104-113):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `title`, `summary`, `tags_json`, `type`
- Index: `idx_knowledge_nodes_project`

**Agent Runs Table (Lines 115-126):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `agent_id`, `status`, `input_prompt`, `output_summary`, `started_at`, `finished_at`
- Index: `idx_agent_runs_project`

**Idea Candidates Table (Lines 128-143):**
- Primary key: `id TEXT`
- Foreign keys: `project_id` → `projects.id`, `source_id` → `ingest_sources.id`
- Fields: `source_doc_id`, `source_doc_chunk_id`, `original_text`, `summary`, `embedding_json`, `cluster_id`, `created_at`
- Indexes: `idx_idea_candidates_project`, `idx_idea_candidates_cluster`

**Idea Clusters Table (Lines 145-155):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `name`, `summary`, `idea_ids_json`, `created_at`, `updated_at`
- Index: `idx_idea_clusters_project`

**Roadmaps Table (Lines 157-166):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `name`, `graph_json`, `created_at`, `updated_at`
- Index: `idx_roadmaps_project`

**Context Items Table (Lines 168-180):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `name`, `type`, `tokens`, `pinned`, `canonical_document_id`, `created_at`
- Indexes: `idx_context_items_project`, `idx_context_items_pinned`

**Agent Steps Table (Lines 182-197):**
- Primary key: `id TEXT`
- Foreign key: `run_id` → `agent_runs.id`
- Fields: `step_number`, `node_id`, `status`, `input_json`, `output_json`, `error`, `duration_ms`, `started_at`, `completed_at`
- Indexes: `idx_agent_steps_run`, `idx_agent_steps_step_number` (composite)

**Agent Messages Table (Lines 199-209):**
- Primary key: `id TEXT`
- Foreign key: `run_id` → `agent_runs.id`
- Fields: `role`, `content`, `context_item_ids_json`, `created_at`
- Indexes: `idx_agent_messages_run`, `idx_agent_messages_created_at` (composite)

**Agent Node States Table (Lines 211-223):**
- Composite primary key: `(run_id, node_id)`
- Foreign key: `run_id` → `agent_runs.id`
- Fields: `status`, `progress`, `messages_json`, `started_at`, `completed_at`, `error`
- Index: `idx_agent_node_states_run`

**Workflow Graphs Table (Lines 225-235):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `name`, `description`, `graph_json`, `created_at`, `updated_at`
- Index: `idx_workflow_graphs_project`

**Workflow Runs Table (Lines 237-257):**
- Primary key: `id TEXT`
- Foreign keys: `project_id` → `projects.id`, `workflow_id` → `workflow_graphs.id`
- Fields: `status`, `input_json`, `output_json`, `started_at`, `finished_at`, `last_message`, `task_id`, `checkpoint_json`, `paused_at`, `cancelled_at`, `estimated_completion`
- Indexes: `idx_workflow_runs_project`, `idx_workflow_runs_status`, `idx_workflow_runs_task_id`

**Workflow Node States Table (Lines 259-271):**
- Composite primary key: `(run_id, node_id)`
- Foreign key: `run_id` → `workflow_runs.id`
- Fields: `status`, `progress`, `messages_json`, `started_at`, `completed_at`, `error`
- Index: `idx_workflow_node_states_run`

**Roadmap Nodes Table (Lines 273-292):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `label`, `description`, `status`, `priority`, `start_date`, `target_date`, `depends_on_ids_json`, `lane_id`, `idea_id`, `ticket_id`, `mission_control_task_id`, `created_at`, `updated_at`
- Indexes: `idx_roadmap_nodes_project`, `idx_roadmap_nodes_status`

**Roadmap Edges Table (Lines 294-308):**
- Primary key: `id TEXT`
- Foreign keys: `project_id` → `projects.id`, `from_node_id` → `roadmap_nodes.id`, `to_node_id` → `roadmap_nodes.id`
- Fields: `kind`, `label`, `created_at`
- Indexes: `idx_roadmap_edges_project`, `idx_roadmap_edges_from`, `idx_roadmap_edges_to`

**Knowledge Edges Table (Lines 310-325):**
- Primary key: `id TEXT`
- Foreign keys: `project_id` → `projects.id`, `source` → `knowledge_nodes.id`, `target` → `knowledge_nodes.id`
- Fields: `type`, `weight`, `label`, `created_at`
- Indexes: `idx_knowledge_edges_project`, `idx_knowledge_edges_source`, `idx_knowledge_edges_target`

**Gap Reports Table (Lines 327-333):**
- Primary key: `id TEXT`
- Foreign key: `project_id` → `projects.id`
- Fields: `generated_at`
- Index: `idx_gap_reports_project`

**Gap Suggestions Table (Lines 335-347):**
- Primary key: `id TEXT`
- Foreign keys: `report_id` → `gap_reports.id`, `project_id` → `projects.id`, `ticket_id` → `idea_tickets.id`
- Fields: `status`, `notes`, `confidence`, `related_files_json`
- Index: `idx_gap_suggestions_report`

### Schema Patterns

**JSON Storage:** Complex types stored as JSON strings:
- `depends_on_ids_json`, `idea_ids_json`, `origin_idea_ids_json`, `tags_json`, `embedding_json`, `graph_json`, `input_json`, `output_json`, `messages_json`, `context_item_ids_json`, `related_files_json`

**Datetime Storage:** All timestamps stored as ISO strings (`TEXT`), not SQLite datetime types.

**Foreign Key Relationships:**
- Most tables reference `projects.id` for multi-tenancy
- Agent tables reference `agent_runs.id`
- Workflow tables reference `workflow_runs.id` and `workflow_graphs.id`
- Roadmap tables reference `roadmap_nodes.id`
- Knowledge tables reference `knowledge_nodes.id`
- Gap analysis references `gap_reports.id` and `idea_tickets.id`

**Index Strategy:**
- Project-scoped queries: `idx_*_project` on `project_id`
- Foreign key lookups: indexes on FK columns
- Status filtering: `idx_*_status` on `status` columns
- Composite indexes: `(run_id, step_number)`, `(run_id, created_at)` for ordered queries

**Composite Primary Keys:**
- `agent_node_states`: `(run_id, node_id)`
- `workflow_node_states`: `(run_id, node_id)`

**Design Notes:**
- WAL mode enables concurrent reads during writes
- JSON fields allow schema flexibility but limit query capabilities
- Foreign key constraints enforced by SQLite (if enabled)
- Indexes optimized for common query patterns (project-scoped, status-filtered, ordered)

---

## Backend Service Layer Analysis

The service layer (`backend/app/services/`) implements business logic for all domain operations, abstracting database access through repositories and coordinating external integrations. Twenty service modules provide comprehensive functionality across authentication, project management, ingestion, agents, workflows, roadmaps, knowledge graphs, context management, ideas, LLM operations, vector search, streaming, and system metrics.

### AuthService (`backend/app/services/auth_service.py`)

**Module-Level Constants (Lines 12-16):**
- `SECRET_KEY`: Retrieved from `get_settings().auth_secret` (line 12)
- `ALGORITHM`: `"HS256"` for JWT signing (line 13)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `30` minutes default expiry (line 14)
- `oauth2_scheme`: `OAuth2PasswordBearer(tokenUrl="/api/token")` for FastAPI dependency injection (line 16)

**TokenData Model (Lines 19-20):** Pydantic `BaseModel` with `username: str | None = None` for token payload extraction.

**create_access_token Function (Lines 23-31):**
- **Parameters:** `data: dict` (payload), `expires_delta: timedelta | None` (optional expiry override)
- **Default Expiry:** 15 minutes if `expires_delta` not provided (line 28)
- **JWT Encoding:** Uses `jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)` from `jose` library (line 30)
- **Expiry Handling:** Adds `exp` claim with UTC datetime (lines 25-29)
- **Return:** Encoded JWT string

**verify_token Function (Lines 34-48):**
- **Dependency Injection:** Uses `Depends(oauth2_scheme)` for automatic token extraction from Authorization header
- **Error Handling:** Raises `HTTPException` 401 with `WWW-Authenticate: Bearer` header on failure (lines 35-39)
- **JWT Decoding:** Uses `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` (line 41)
- **Subject Extraction:** Extracts `username` from `sub` claim (line 42)
- **Validation:** Raises exception if `username` is None (lines 43-44)
- **Exception Handling:** Catches `JWTError` and re-raises as credentials exception (lines 46-47)
- **Return:** `TokenData` object with username

**Security Considerations:**
- Secret key must be changed in production (default "a_very_secret_key")
- Token expiry enforced via `exp` claim
- No refresh token mechanism (single access token)
- No token revocation (tokens valid until expiry)

### ProjectService (`backend/app/services/project_service.py`)

**Class Definition (Lines 18-53):** `ProjectService` wraps `ProjectRepository` with business logic and HTTP exception handling.

**Constructor (Lines 19-20):** `__init__(self, repo: ProjectRepository)` stores repository instance.

**list_projects Method (Lines 22-23):**
- **Delegation:** Directly delegates to `repo.list_projects(cursor, limit)`
- **No Business Logic:** Pure pass-through to repository

**get_project Method (Lines 25-29):**
- **Repository Call:** `repo.get_project(project_id)` returns `Optional[CortexProject]`
- **Error Handling:** Raises `HTTPException` 404 if project not found (lines 27-28)
- **Return:** `CortexProject` (guaranteed non-None)

**create_project Method (Lines 31-36):**
- **Slug Generation:** Uses `ProjectFactory._slugify(request.name)` if slug not provided (line 32)
- **Slug Validation:** Checks for existing slug via `repo.get_by_slug()` (line 32)
- **Conflict Handling:** Raises `HTTPException` 409 if slug already exists (lines 33-34)
- **Project Creation:** Uses `ProjectFactory.new()` to create domain object (line 35)
- **Persistence:** Saves via `repo.save(project)` (line 36)

**update_project Method (Lines 38-47):**
- **Existence Check:** Verifies project exists before update (lines 39-41)
- **Field Filtering:** Uses `request.model_dump(exclude_none=True)` to only include provided fields (line 43)
- **Repository Update:** Calls `repo.update(project_id, fields)` (line 44)
- **Error Handling:** Raises 500 if update returns None (lines 45-46)
- **Return:** Updated `CortexProject`

**delete_project Method (Lines 49-53):**
- **Repository Call:** `repo.delete(project_id)` returns boolean
- **Error Handling:** Raises 404 if deletion fails (lines 51-52)
- **Return:** `DeleteProjectResponse(success=True)`

**get_project_service Factory (Lines 56-57):** Dependency injection helper creating `ProjectService(get_project_repo())`.

### IngestService (`backend/app/services/ingest_service.py`)

**Class Definition (Lines 15-333):** `IngestService` manages ingest job lifecycle with file processing and RAG integration.

**list_jobs Method (Lines 16-68):**
- **Query Building:** Constructs SQL query with optional filters for `status`, `stage`, `source_id` (lines 25-37)
- **Pagination:** Fetches `limit + 1` rows to detect next page (line 40)
- **Cursor Logic:** Uses last row ID as next cursor if more rows available (lines 48-50)
- **Total Count:** Separate COUNT query with same filters (lines 52-66)
- **Row Mapping:** Converts database rows to `IngestJob` via `_row_to_job()` (line 46)
- **Return:** `PaginatedResponse` with items, next_cursor, total

**get_job Method (Lines 70-75):**
- **Query:** Single-row SELECT by `job_id`
- **Row Mapping:** Uses `_row_to_job()` if row exists
- **Return:** `Optional[IngestJob]` (None if not found)

**create_job Method (Lines 77-141):**
- **Source Management:** Creates default source if none exists for project (lines 81-99)
- **Filename Extraction:** Extracts filename from `source_path` using `split("/")[-1]` (line 101)
- **Job Creation:** Creates `IngestJob` with `QUEUED` status, `0.0` progress, `"initial"` stage (lines 102-113)
- **Database Insert:** Inserts into `ingest_jobs` table with all fields (lines 115-133)
- **Event Emission:** Emits `ingest.job.created` event via `asyncio.create_task(emit_ingest_event())` (lines 136-139)
- **Return:** Created `IngestJob`

**cancel_job Method (Lines 143-164):**
- **Status Update:** Sets status to `CANCELLED`, updates `updated_at` and `completed_at` (lines 145-154)
- **Event Emission:** Emits `ingest.job.cancelled` event after update (lines 158-162)
- **Return:** Updated `IngestJob`

**delete_job Method (Lines 166-169):**
- **Direct Delete:** Executes `DELETE FROM ingest_jobs WHERE id = ?` (line 168)
- **No Validation:** Does not check job status before deletion
- **No Return:** Void method

**process_job Method (Lines 171-256):**
- **Job Retrieval:** Gets job by ID, returns early if not found (lines 172-174)
- **Event Emission:** Emits `ingest.job.started` event (lines 176-182)
- **Status Update:** Sets status to `RUNNING`, progress to `0.1` (line 184)
- **File Existence Check:** Creates dummy test file if missing and path contains "test-" or "temp" (lines 188-195)
- **File Reading:** Handles PDF via `pypdf` library (lines 201-213) or text files with UTF-8/latin-1 fallback (lines 214-228)
- **RAG Integration:** Calls `rag_service.ingest_document(text, metadata)` (lines 230-235)
- **Success Handling:** Updates status to `COMPLETED`, progress to `1.0`, emits `ingest.job.completed` (lines 237-249)
- **Error Handling:** Updates status to `FAILED`, emits `ingest.job.failed` with error message (lines 250-256)

**update_job Method (Lines 258-311):**
- **Dynamic Updates:** Builds UPDATE query with only provided fields (lines 268-286)
- **Field Mapping:** Maps `message` parameter to `error_message` column (lines 278-280)
- **Timestamp Update:** Always updates `updated_at` (lines 288-289)
- **Event Emission:** Maps status to event type and emits appropriate event (lines 298-309)
- **Return:** Updated `IngestJob` or None

**_row_to_job Helper (Lines 313-330):**
- **Row Mapping:** Converts database row to `IngestJob` Pydantic model
- **Datetime Parsing:** Uses `datetime.fromisoformat()` for timestamp fields (lines 322-324)
- **Status Enum:** Converts string status to `IngestStatus` enum (line 325)
- **Default Values:** Uses `row.get()` with defaults for optional fields

**Module-Level Instance (Line 333):** `ingest_service = IngestService()` singleton instance.

### AgentService (`backend/app/services/agent_service.py`)

**Class Definition (Lines 28-611):** `AgentService` manages agent profiles, runs, steps, messages, and node states with LangGraph integration.

**Constructor (Lines 35-49):**
- **Agent Registry:** In-memory `Dict[str, AgentProfile]` with two predefined agents:
  - `"researcher"`: Deep Researcher with capabilities ["deep_research", "citation", "summarization"]
  - `"planner"`: Strategy Planner with capabilities ["planning", "decomposition", "timeline_synthesis"]
- **No Database:** Agent profiles stored in memory, not persisted

**list_agents Method (Lines 51-52):** Returns list of all registered agent profiles.

**get_agent Method (Lines 54-55):** Returns `Optional[AgentProfile]` by ID from registry.

**list_runs Method (Lines 57-65):**
- **Project Filtering:** Optional `project_id` filter (lines 59-62)
- **Ordering:** Orders by `started_at DESC` (lines 61, 64)
- **Row Mapping:** Converts rows to `AgentRun` via `_row_to_run()` (line 65)
- **Return:** `List[AgentRun]` (not paginated)

**get_run Method (Lines 67-72):**
- **Query:** Single-row SELECT by `run_id`
- **Row Mapping:** Uses `_row_to_run()` if found
- **Return:** `Optional[AgentRun]`

**create_run_record Method (Lines 74-108):**
- **ID Generation:** Uses `uuid.uuid4()` for run ID (line 75)
- **Run Creation:** Creates `AgentRun` with `PENDING` status (lines 77-88)
- **Database Insert:** Inserts into `agent_runs` table (lines 89-107)
- **No Execution:** Does not start execution (handled separately)
- **Return:** Created `AgentRun`

**update_run Method (Lines 110-156):**
- **Partial Updates:** Updates only provided fields (`status`, `output_summary`, `finished`)
- **Existence Check:** Returns None if run not found (lines 118-120)
- **Finished Handling:** Sets `finished_at` timestamp if `finished=True` (lines 126-127)
- **Database Update:** Updates `agent_runs` table (lines 129-141)
- **Event Emission:** Maps status to event type (`agent.run.started`, `agent.run.completed`, etc.) and emits (lines 143-154)
- **Return:** Updated `AgentRun` or None

**cancel_run Method (Lines 158-179):**
- **Status Update:** Sets status to `CANCELLED`, `finished_at` to current time (lines 159-169)
- **Event Emission:** Emits `agent.run.cancelled` event (lines 173-177)
- **Return:** Updated `AgentRun`

**list_steps Method (Lines 181-202):**
- **Ordering:** Orders by `step_number ASC` (line 188)
- **Pagination:** Fetches `limit + 1` rows, uses last ID as cursor (lines 189-197)
- **Total Count:** Separate COUNT query (line 199)
- **Row Mapping:** Uses `_row_to_step()` (line 193)
- **Return:** `PaginatedResponse[AgentStep]`

**create_step Method (Lines 204-238):**
- **ID Generation:** Uses `uuid.uuid4()` for step ID (line 211)
- **Step Creation:** Creates `AgentStep` with provided `step_number`, `node_id`, `status` (lines 213-220)
- **Database Insert:** Inserts into `agent_steps` table (lines 221-237)
- **Return:** Created `AgentStep`

**update_step Method (Lines 240-283):**
- **Dynamic Updates:** Builds UPDATE query with provided fields (`status`, `input`, `output`, `error`, `duration_ms`, `completed`)
- **JSON Serialization:** Serializes `input` and `output` to JSON strings (lines 258-263)
- **Completion Handling:** Sets `completed_at` timestamp if `completed=True` (lines 270-272)
- **Return:** Updated `AgentStep` or None

**list_messages Method (Lines 285-308):**
- **Ordering:** Orders by `created_at ASC` (chronological) (line 292)
- **Pagination:** Fetches `limit + 1` rows (lines 293-301)
- **Total Count:** Separate COUNT query (lines 303-305)
- **Row Mapping:** Uses `_row_to_message()` (line 297)
- **Return:** `PaginatedResponse[AgentMessage]`

**append_message Method (Lines 310-346):**
- **ID Generation:** Uses `uuid.uuid4()` for message ID (line 311)
- **Message Creation:** Creates `AgentMessage` with `USER` role, content, context_item_ids (lines 313-320)
- **Database Insert:** Inserts into `agent_messages` table with JSON-serialized context_item_ids (lines 321-337)
- **Event Emission:** Emits `agent.message.appended` event (lines 339-344)
- **Return:** Created `AgentMessage`

**list_node_states Method (Lines 348-351):**
- **Query:** SELECT all node states for run_id
- **Row Mapping:** Uses `_row_to_node_state()` (line 351)
- **Return:** `List[AgentNodeState]` (not paginated)

**update_node_state Method (Lines 353-420):**
- **Upsert Logic:** Checks if node state exists, updates or inserts accordingly (lines 367-414)
- **Dynamic Updates:** Builds UPDATE query with provided fields (`status`, `progress`, `messages`, `error`, `started`, `completed`)
- **JSON Serialization:** Serializes `messages` list to JSON (line 383)
- **Timestamp Handling:** Sets `started_at` or `completed_at` based on flags (lines 388-393)
- **Composite Key:** Uses `(run_id, node_id)` as composite key
- **Return:** `AgentNodeState` (always returns, creates if missing)

**execute_run Method (Lines 422-523):**
- **Status Update:** Sets run status to `RUNNING` (line 426)
- **LangGraph Integration:** Imports `project_manager_graph` app (line 430)
- **Node State Initialization:** Creates initial node state for "agent" node (line 433)
- **Event Streaming:** Uses `langgraph_app.astream_events()` to stream execution events (lines 436-439)
- **Event Handling:**
  - `on_chain_start`: Updates node state to "running", emits `agent.step.started` (lines 441-459)
  - `on_chain_end`: Updates node state to "completed", emits `agent.step.completed` (lines 461-479)
  - `on_chain_error`: Updates node state to "failed", emits `agent.step.failed` (lines 481-501)
- **Final State:** Invokes graph to get final state, extracts output from last message (lines 504-506)
- **Completion:** Updates run status to `COMPLETED` with output summary (lines 508-513)
- **Error Handling:** Catches exceptions, updates run to `FAILED`, marks nodes as failed (lines 515-522)

**Row Mapping Helpers:**
- **`_row_to_run` (Lines 524-544):** Parses JSON context_item_ids, converts status enum, handles optional finished_at
- **`_row_to_step` (Lines 546-572):** Parses JSON input/output, handles JSON decode errors gracefully
- **`_row_to_message` (Lines 574-589):** Parses JSON context_item_ids, converts role enum
- **`_row_to_node_state` (Lines 591-608):** Parses JSON messages, handles optional timestamps and error

**Module-Level Instance (Line 611):** `agent_service = AgentService()` singleton instance.

### WorkflowService (`backend/app/services/workflow_service.py`)

**Class Definition (Lines 26-650):** `WorkflowService` manages workflow graphs, runs, node states, and LangGraph execution.

**list_graphs Method (Lines 31-37):**
- **Project Filtering:** Optional `project_id` filter (lines 33-36)
- **Row Mapping:** Uses `_row_to_graph()` to deserialize JSON graph (line 37)
- **Return:** `List[WorkflowGraph]`

**get_graph Method (Lines 39-44):**
- **Query:** Single-row SELECT by `workflow_id`
- **Row Mapping:** Uses `_row_to_graph()` if found
- **Return:** `Optional[WorkflowGraph]`

**create_graph Method (Lines 46-86):**
- **ID Generation:** Uses `uuid.uuid4()` for graph ID (line 47)
- **Graph Parsing:** Parses `nodes` and `edges` from `graph_data` dict (lines 51-52)
- **Graph Creation:** Creates `WorkflowGraph` with `WorkflowNode` and `WorkflowEdge` objects (lines 54-60)
- **JSON Serialization:** Serializes graph to JSON for storage (lines 74-79)
- **Database Insert:** Inserts into `workflow_graphs` table (lines 62-84)
- **Return:** Created `WorkflowGraph`

**list_runs Method (Lines 88-103):**
- **Filtering:** Optional `project_id` and `workflow_id` filters (lines 93-98)
- **Ordering:** Orders by `started_at DESC` (line 100)
- **Row Mapping:** Uses `_row_to_run()` (line 103)
- **Return:** `List[WorkflowRun]`

**get_run Method (Lines 105-110):**
- **Query:** Single-row SELECT by `run_id`
- **Row Mapping:** Uses `_row_to_run()` if found
- **Return:** `Optional[WorkflowRun]`

**create_run Method (Lines 112-149):**
- **ID Generation:** Uses `uuid.uuid4()` for run ID (line 118)
- **Run Creation:** Creates `WorkflowRun` with `PENDING` status (lines 121-128)
- **JSON Serialization:** Serializes `input_data` to JSON (line 142)
- **Database Insert:** Inserts into `workflow_runs` table (lines 130-147)
- **Return:** Created `WorkflowRun`

**update_run_status Method (Lines 151-199):**
- **Dynamic Updates:** Builds UPDATE query with provided fields (`status`, `last_message`, `output_data`, `finished`)
- **JSON Serialization:** Serializes `output_data` to JSON (lines 169-171)
- **Finished Handling:** Sets `finished_at` timestamp if `finished=True` (lines 172-174)
- **Event Emission:** Emits `workflow.run.updated` event after update (lines 190-197)
- **Return:** Updated `WorkflowRun` or None

**get_node_state Method (Lines 201-208):**
- **Composite Key:** Queries by `(run_id, node_id)`
- **Row Mapping:** Uses `_row_to_node_state()` if found
- **Return:** `Optional[WorkflowNodeState]`

**set_node_state Method (Lines 210-296):**
- **Upsert Logic:** Checks if node state exists, updates or inserts accordingly (lines 224-273)
- **Dynamic Updates:** Builds UPDATE query with provided fields (`status`, `progress`, `messages`, `error`, `started`, `completed`)
- **JSON Serialization:** Serializes `messages` list to JSON (line 241)
- **Timestamp Handling:** Sets `started_at` or `completed_at` based on flags (lines 246-251)
- **Event Emission:** Emits `workflow.node_state.updated` event (lines 280-294)
- **Return:** `WorkflowNodeState` (always returns, creates if missing)

**list_node_states Method (Lines 298-301):**
- **Query:** SELECT all node states for run_id
- **Row Mapping:** Uses `_row_to_node_state()` (line 301)
- **Return:** `List[WorkflowNodeState]`

**execute_workflow_run Method (Lines 303-403):**
- **Run Validation:** Verifies run and workflow graph exist (lines 305-313)
- **Project ID Retrieval:** Gets project_id from database (lines 315-322)
- **Status Update:** Sets run status to `RUNNING` (line 325)
- **Event Emission:** Emits `workflow.run.created` event (lines 327-334)
- **Graph Compilation:** Uses `WorkflowGraphCompiler` to compile graph to LangGraph `StateGraph` (lines 337-339)
- **Input Data Retrieval:** Loads `input_json` from database (lines 341-344)
- **Initial State:** Prepares state dict with run_id, project_id, input, output, messages, current_node (lines 346-354)
- **Event Streaming:** Uses `compiled_graph.astream_events()` to stream execution events (line 357)
- **Event Handling:** Calls `_handle_execution_event()` for each event (line 359)
- **Final State:** Invokes graph to get final state (line 362)
- **Completion:** Updates run status to `COMPLETED` with output data, emits `workflow.run.completed` (lines 363-378)
- **Cancellation Handling:** Catches `asyncio.CancelledError`, updates to `CANCELLED`, emits event (lines 380-391)
- **Error Handling:** Catches exceptions, updates to `FAILED`, emits event (lines 392-403)

**`_handle_execution_event` Method (Lines 405-451):**
- **Event Type Detection:** Extracts `event_type` and `name` from event dict (lines 407-408)
- **`on_chain_start`:** Sets node state to `RUNNING`, emits `workflow.node.started` (lines 410-420)
- **`on_chain_end`:** Sets node state to `COMPLETED`, extracts output, emits `workflow.node.completed` (lines 422-439)
- **`on_chain_error`:** Sets node state to `FAILED`, emits `workflow.node.failed` (lines 441-451)

**cancel_workflow_run Method (Lines 453-502):**
- **Run Validation:** Verifies run exists and is cancellable (lines 455-460)
- **Status Update:** Sets status to `CANCELLED`, sets `cancelled_at` and `finished_at` timestamps (lines 468-484)
- **Node Cancellation:** Cancels all running nodes (lines 486-490)
- **Event Emission:** Emits `workflow.run.cancelled` event (lines 492-500)
- **Return:** Updated `WorkflowRun`

**pause_workflow_run Method (Lines 504-541):**
- **Run Validation:** Verifies run exists and is `RUNNING` (lines 506-511)
- **Status Update:** Sets status to `PAUSED`, sets `paused_at`, stores `checkpoint_json` (lines 518-528)
- **Checkpoint Storage:** Serializes checkpoint data to JSON for resume capability
- **Event Emission:** Emits `workflow.run.paused` event (lines 531-539)
- **Return:** Updated `WorkflowRun`

**resume_workflow_run Method (Lines 543-582):**
- **Run Validation:** Verifies run exists and is `PAUSED` (lines 545-550)
- **Status Update:** Sets status to `RUNNING`, clears `paused_at` (lines 557-567)
- **Execution Resume:** Schedules `execute_workflow_run()` as background task (line 570)
- **Event Emission:** Emits `workflow.run.resumed` event (lines 572-580)
- **Return:** Updated `WorkflowRun`

**get_execution_status Method (Lines 584-611):**
- **Run Validation:** Verifies run exists (lines 586-588)
- **Node States:** Retrieves all node states for run (line 590)
- **Progress Calculation:** Computes average progress across all nodes (lines 592-595)
- **Current Node Detection:** Finds first node with `RUNNING` status (lines 597-602)
- **Return:** Dict with run_id, status, progress, current_node, started_at, node_states

**Row Mapping Helpers:**
- **`_row_to_graph` (Lines 613-621):** Deserializes `graph_json`, reconstructs `WorkflowNode` and `WorkflowEdge` objects
- **`_row_to_run` (Lines 623-634):** Converts status enum, parses timestamps, handles optional fields
- **`_row_to_node_state` (Lines 636-647):** Validates JSON messages, converts status enum, handles optional progress

**Module-Level Instance (Line 650):** `workflow_service = WorkflowService()` singleton instance.

### RoadmapService (`backend/app/services/roadmap_service.py`)

**Class Definition (Lines 20-408):** `RoadmapService` manages roadmap nodes and edges with DAG validation and cycle detection.

**list_nodes Method (Lines 26-69):**
- **Filtering:** Optional `status` and `lane_id` filters (lines 38-43)
- **Ordering:** Orders by `created_at DESC` (line 45)
- **Pagination:** Fetches `limit + 1` rows, uses last ID as cursor (lines 46-54)
- **Total Count:** Separate COUNT query with same filters (lines 56-67)
- **Row Mapping:** Uses `_row_to_node()` (line 50)
- **Return:** `PaginatedResponse[RoadmapNode]`

**get_node Method (Lines 71-78):**
- **Query:** Single-row SELECT by `node_id` and `project_id`
- **Row Mapping:** Uses `_row_to_node()` if found
- **Return:** `Optional[RoadmapNode]`

**create_node Method (Lines 80-139):**
- **ID Generation:** Uses `uuid.uuid4()` for node ID (line 81)
- **Dependency Validation:** Validates `depends_on_ids` exist via `_validate_dependencies()` (lines 85-87)
- **Status Normalization:** Converts status to uppercase, validates against enum (line 90)
- **Priority Normalization:** Converts priority to uppercase if provided (line 91)
- **Node Creation:** Creates `RoadmapNode` with all fields (lines 93-109)
- **JSON Serialization:** Serializes `depends_on_ids` list to JSON (line 128)
- **Database Insert:** Inserts into `roadmap_nodes` table (lines 111-137)
- **Return:** Created `RoadmapNode`

**update_node Method (Lines 141-192):**
- **Existence Check:** Verifies node exists and belongs to project (lines 143-148)
- **Dependency Validation:** Validates new dependencies if updating (lines 151-157)
- **Cycle Detection:** Checks for circular dependencies via `_has_circular_dependency()` (lines 156-157)
- **Dynamic Updates:** Builds UPDATE query with provided fields (lines 159-179)
- **Timestamp Update:** Always updates `updated_at` (lines 181-182)
- **Return:** Updated `RoadmapNode`

**delete_node Method (Lines 194-211):**
- **Dependency Check:** Verifies no other nodes depend on this node (lines 196-202)
- **Edge Cleanup:** Deletes all edges connected to node (lines 204-208)
- **Node Deletion:** Deletes node itself (line 210)
- **Error Handling:** Raises `ValueError` if dependencies exist

**list_edges Method (Lines 213-236):**
- **Ordering:** Orders by `created_at DESC` (line 220)
- **Pagination:** Fetches `limit + 1` rows (lines 221-229)
- **Total Count:** Separate COUNT query (lines 231-233)
- **Row Mapping:** Uses `_row_to_edge()` (line 225)
- **Return:** `PaginatedResponse[RoadmapEdge]`

**create_edge Method (Lines 238-295):**
- **ID Generation:** Uses `uuid.uuid4()` for edge ID (line 239)
- **Node Validation:** Verifies source and target nodes exist (lines 246-251)
- **Duplicate Check:** Verifies edge doesn't already exist (lines 253-260)
- **Cycle Detection:** Checks if edge would create cycle via `_would_create_cycle()` (lines 262-264)
- **Edge Creation:** Creates `RoadmapEdge` with `depends_on` or `relates_to` kind (lines 266-274)
- **Database Insert:** Inserts into `roadmap_edges` table (lines 276-293)
- **Return:** Created `RoadmapEdge`

**delete_edge Method (Lines 297-300):**
- **Direct Delete:** Executes `DELETE FROM roadmap_edges WHERE id = ? AND project_id = ?`
- **No Validation:** Does not check for dependent nodes

**get_graph Method (Lines 302-310):**
- **Node Retrieval:** Lists all nodes with high limit (1000) (line 303)
- **Edge Retrieval:** Lists all edges with high limit (1000) (line 304)
- **Graph Construction:** Creates `RoadmapGraph` with nodes, edges, generated_at timestamp (lines 306-310)
- **Return:** `RoadmapGraph`

**`_validate_dependencies` Method (Lines 312-319):**
- **Dependency Check:** Verifies each dependency ID exists in project
- **Error Handling:** Raises `ValueError` if any dependency not found

**`_has_circular_dependency` Method (Lines 321-345):**
- **DFS Algorithm:** Uses depth-first search to detect cycles
- **Visited Tracking:** Maintains `visited` set to prevent infinite loops
- **Cycle Detection:** Returns True if DFS reaches `node_id` (indicating cycle)
- **Edge Traversal:** Follows edges from current node to target nodes

**`_would_create_cycle` Method (Lines 347-368):**
- **DFS Algorithm:** Similar to `_has_circular_dependency` but checks if adding edge `from_node_id -> to_node_id` would create cycle
- **Cycle Detection:** Returns True if DFS from `to_node_id` reaches `from_node_id`

**Row Mapping Helpers:**
- **`_row_to_node` (Lines 370-394):** Parses JSON depends_on_ids, converts status/priority enums, handles optional dates
- **`_row_to_edge` (Lines 396-405):** Converts edge kind enum, handles optional label

**Module-Level Instance (Line 408):** `roadmap_service = RoadmapService()` singleton instance.

### KnowledgeService (`backend/app/services/knowledge_service.py`)

**Class Definition (Lines 19-428):** `KnowledgeService` manages knowledge graph nodes and edges with Qdrant vector search integration.

**get_graph Method (Lines 24-58):**
- **Node Retrieval:** Lists all nodes with high limit (1000) (line 30)
- **Edge Retrieval:** Lists all edges with high limit (1000) (line 31)
- **View Filtering:** Filters nodes by type if `view` parameter provided ("ideas", "tickets", "docs") (lines 34-40)
- **Focus Node:** If `focus_node_id` provided, includes only that node and its neighbors (lines 43-52)
- **Graph Construction:** Creates `KnowledgeGraph` with filtered nodes/edges, generated_at timestamp (lines 54-58)
- **Return:** `KnowledgeGraph`

**get_node Method (Lines 60-67):**
- **Query:** Single-row SELECT by `node_id` and `project_id`
- **Row Mapping:** Uses `_row_to_node()` if found
- **Return:** `Optional[KnowledgeNode]`

**get_node_neighbors Method (Lines 69-108):**
- **Node Validation:** Verifies node exists (lines 70-72)
- **Edge Query:** Finds all edges connected to node (source or target) (lines 74-82)
- **Neighbor Collection:** Collects neighbor IDs from edges (lines 84-92)
- **Neighbor Retrieval:** Fetches neighbor nodes from database (lines 94-102)
- **Return:** Dict with `node`, `neighbors`, `edges`

**list_nodes Method (Lines 110-133):**
- **Ordering:** Orders by `created_at DESC` (line 117)
- **Pagination:** Fetches `limit + 1` rows, uses last ID as cursor (lines 118-126)
- **Total Count:** Separate COUNT query (lines 128-130)
- **Row Mapping:** Uses `_row_to_node()` (line 122)
- **Return:** `PaginatedResponse[KnowledgeNode]`

**create_node Method (Lines 135-180):**
- **ID Generation:** Uses `uuid.uuid4()` for node ID (line 136)
- **Node Creation:** Creates `KnowledgeNode` with title, summary, text, type, tags, metadata (lines 139-150)
- **Database Insert:** Inserts into `knowledge_nodes` table with JSON-serialized tags (lines 152-168)
- **Qdrant Integration:** Calls `qdrant_service.upsert_knowledge_node()` to store embedding (lines 170-178)
- **Return:** Created `KnowledgeNode`

**update_node Method (Lines 182-226):**
- **Existence Check:** Verifies node exists and belongs to project (lines 184-189)
- **Dynamic Updates:** Builds UPDATE query with provided fields (`title`, `summary`, `tags`)
- **JSON Serialization:** Serializes `tags` list to JSON (lines 200-202)
- **Qdrant Update:** Updates embedding in Qdrant if title/summary changed (lines 215-224)
- **Return:** Updated `KnowledgeNode`

**list_edges Method (Lines 228-251):**
- **Ordering:** Orders by `created_at DESC` (line 235)
- **Pagination:** Fetches `limit + 1` rows (lines 236-244)
- **Total Count:** Separate COUNT query (lines 246-248)
- **Row Mapping:** Uses `_row_to_edge()` (line 240)
- **Return:** `PaginatedResponse[KnowledgeEdge]`

**create_edge Method (Lines 253-308):**
- **ID Generation:** Uses `uuid.uuid4()` for edge ID (line 254)
- **Node Validation:** Verifies source and target nodes exist (lines 260-266)
- **Duplicate Check:** Verifies edge doesn't already exist (lines 268-275)
- **Edge Creation:** Creates `KnowledgeEdge` with type, weight, label (lines 277-286)
- **Database Insert:** Inserts into `knowledge_edges` table (lines 288-306)
- **Return:** Created `KnowledgeEdge`

**delete_edge Method (Lines 310-313):**
- **Direct Delete:** Executes `DELETE FROM knowledge_edges WHERE id = ? AND project_id = ?`
- **No Validation:** Does not check for dependent nodes

**search Method (Lines 315-392):**
- **Vector Search:** Attempts Qdrant vector search if `useVectorSearch=True` and Qdrant available (lines 323-361)
- **Query Embedding:** Generates embedding for query text via `qdrant_service`
- **Node Type Filter:** Applies filter if `type` parameter provided
- **Result Mapping:** Fetches full node data from database, adds similarity scores to metadata (lines 334-361)
- **Text Search Fallback:** Falls back to SQL LIKE query if vector search unavailable (lines 363-392)
- **Scoring:** Simple scoring based on title/summary matches (lines 379-388)
- **Return:** `List[KnowledgeNode]` ordered by similarity score

**Row Mapping Helpers:**
- **`_row_to_node` (Lines 394-413):** Parses JSON tags, handles optional text/metadata fields
- **`_row_to_edge` (Lines 415-425):** Handles optional weight/label fields

**Module-Level Instance (Line 428):** `knowledge_service = KnowledgeService()` singleton instance.

### ContextService (`backend/app/services/context_service.py`)

**Class Definition (Lines 17-162):** `ContextService` manages context items with token budget tracking.

**Class Constant (Line 22):** `DEFAULT_MAX_TOKENS = 100000` default project token limit.

**list_items Method (Lines 24-32):**
- **Project Filtering:** Optional `project_id` filter (lines 26-31)
- **Ordering:** Orders by `created_at DESC` (lines 28, 31)
- **Row Mapping:** Uses `_row_to_item()` (line 32)
- **Return:** `List[ContextItem]`

**get_budget Method (Lines 34-46):**
- **Item Retrieval:** Lists all items for project (line 35)
- **Token Calculation:** Sums `tokens` from all items (line 36)
- **Budget Construction:** Creates `ContextBudget` with total_tokens, used_tokens, available_tokens, items (lines 40-46)
- **Return:** `ContextBudget`

**add_items Method (Lines 48-97):**
- **Budget Check:** Calculates current budget and new token total (lines 50-51)
- **Overflow Validation:** Raises `ValueError` if adding items would exceed budget (lines 53-57)
- **Atomic Insert:** Inserts all items in single transaction (lines 62-94)
- **ID Handling:** Uses provided item ID or generates UUID (line 64)
- **Type Conversion:** Converts `pinned` boolean to integer (0/1) (line 88)
- **Budget Update:** Returns updated budget after insertion (line 96)
- **Return:** `AddContextItemsResponse` with created items and updated budget

**update_item Method (Lines 99-134):**
- **Existence Check:** Verifies item exists and belongs to project (lines 108-113)
- **Partial Updates:** Updates only provided fields (`pinned`, `tokens`)
- **Type Conversion:** Converts `pinned` boolean to integer (line 120)
- **Dynamic Query:** Builds UPDATE query with provided fields (lines 115-129)
- **Return:** Updated `ContextItem`

**remove_item Method (Lines 136-148):**
- **Existence Check:** Verifies item exists and belongs to project (lines 138-143)
- **Deletion:** Executes `DELETE FROM context_items WHERE id = ? AND project_id = ?` (line 145)
- **Budget Return:** Returns updated budget after removal (line 148)
- **Return:** `ContextBudget`

**`_row_to_item` Helper (Lines 150-159):**
- **Row Mapping:** Converts database row to `ContextItem` Pydantic model
- **Type Conversion:** Converts integer `pinned` to boolean (line 156)
- **Enum Conversion:** Converts string type to `ContextItemType` enum (line 154)

**Module-Level Instance (Line 162):** `context_service = ContextService()` singleton instance.

### IdeaService (`backend/app/services/idea_service.py`)

**Class Definition (Lines 25-511):** `IdeaService` manages idea candidates, clusters, tickets, and mission control tasks.

**list_candidates Method (Lines 30-65):**
- **Filtering:** Optional `status` and `type` filters (lines 42-47)
- **Ordering:** Orders by `created_at DESC` (line 49)
- **Pagination:** Fetches `limit + 1` rows, uses last ID as cursor (lines 50-58)
- **Total Count:** Separate COUNT query (lines 60-63)
- **Row Mapping:** Uses `_row_to_candidate()` (line 54)
- **Return:** `PaginatedResponse[IdeaCandidate]`

**create_candidate Method (Lines 67-106):**
- **ID Generation:** Uses `uuid.uuid4()` for candidate ID (line 68)
- **Candidate Creation:** Creates `IdeaCandidate` with type, summary, status, confidence, source fields (lines 71-82)
- **Database Insert:** Inserts into `idea_candidates` table (lines 84-104)
- **Field Mapping:** Maps domain model fields to database columns (source_id, source_doc_id, etc.)
- **Return:** Created `IdeaCandidate`

**update_candidate Method (Lines 108-135):**
- **Existence Check:** Verifies candidate exists and belongs to project (lines 110-114)
- **Dynamic Updates:** Builds UPDATE query with provided fields (`status`, `summary`)
- **Return:** Updated `IdeaCandidate`

**list_clusters Method (Lines 137-160):**
- **Ordering:** Orders by `created_at DESC` (line 144)
- **Pagination:** Fetches `limit + 1` rows (lines 145-153)
- **Total Count:** Separate COUNT query (lines 155-158)
- **Row Mapping:** Uses `_row_to_cluster()` (line 149)
- **Return:** `PaginatedResponse[IdeaCluster]`

**create_cluster Method (Lines 162-197):**
- **ID Generation:** Uses `uuid.uuid4()` for cluster ID (line 163)
- **Cluster Creation:** Creates `IdeaCluster` with label, description, color, idea_ids, priority (lines 166-176)
- **JSON Serialization:** Serializes `idea_ids` list to JSON (line 190)
- **Database Insert:** Inserts into `idea_clusters` table (lines 178-195)
- **Return:** Created `IdeaCluster`

**list_tickets Method (Lines 199-230):**
- **Filtering:** Optional `status` filter (lines 210-212)
- **Ordering:** Orders by `created_at DESC` (line 214)
- **Pagination:** Fetches `limit + 1` rows (lines 215-223)
- **Total Count:** Separate COUNT query (lines 225-228)
- **Row Mapping:** Uses `_row_to_ticket()` (line 219)
- **Return:** `PaginatedResponse[IdeaTicket]`

**create_ticket Method (Lines 232-278):**
- **ID Generation:** Uses `uuid.uuid4()` for ticket ID (line 233)
- **Ticket Creation:** Creates `IdeaTicket` with title, description, status, priority, origin fields (lines 236-253)
- **JSON Serialization:** Serializes `origin_idea_ids` list to JSON (line 273)
- **Database Insert:** Inserts into `idea_tickets` table (lines 255-276)
- **Field Mapping:** Maps `idea_id` to `cluster_id` column (line 266)
- **Return:** Created `IdeaTicket`

**list_tasks Method (Lines 280-321):**
- **Column Mapping:** Maps column names (backlog/todo/in_progress/done) to status values (lines 295-300)
- **Filtering:** Applies status filter if column provided (lines 301-303)
- **Ordering:** Orders by `created_at DESC` (line 305)
- **Pagination:** Fetches `limit + 1` rows (lines 306-314)
- **Row Mapping:** Uses `_ticket_row_to_task()` to convert tickets to tasks (line 310)
- **Return:** `PaginatedResponse[MissionControlTask]`

**create_task Method (Lines 323-383):**
- **ID Generation:** Uses `uuid.uuid4()` for task ID (line 324)
- **Context Extraction:** Extracts context items from task_data (lines 327-338)
- **Task Creation:** Creates `MissionControlTask` with title, origin, confidence, column, context, priority (lines 340-353)
- **Database Storage:** Stores as ticket in `idea_tickets` table with JSON-serialized description (lines 355-381)
- **Description Serialization:** Serializes origin, confidence, column to JSON in description field (lines 367-373)
- **Return:** Created `MissionControlTask`

**update_task Method (Lines 385-425):**
- **Existence Check:** Verifies task (ticket) exists and belongs to project (lines 387-391)
- **Column Mapping:** Maps column updates to status values (lines 399-409)
- **Dynamic Updates:** Builds UPDATE query with provided fields (`title`, `column`, `priority`)
- **Timestamp Update:** Always updates `updated_at` (lines 415-416)
- **Return:** Updated `MissionControlTask`

**Row Mapping Helpers:**
- **`_row_to_candidate` (Lines 427-439):** Maps database row to `IdeaCandidate` with defaults for missing fields
- **`_row_to_cluster` (Lines 441-459):** Parses JSON idea_ids, maps name/summary to label/description
- **`_row_to_ticket` (Lines 461-485):** Parses JSON origin_idea_ids, converts status/priority enums, provides defaults for missing fields
- **`_ticket_row_to_task` (Lines 487-508):** Parses JSON description to extract origin/confidence/column, converts to `MissionControlTask`

**Module-Level Instance (Line 511):** `idea_service = IdeaService()` singleton instance.

### LLMService (`backend/app/services/llm_service.py`)

**Module-Level Setup (Lines 14-20):**
- **Settings Retrieval:** Gets settings via `get_settings()` (line 14)
- **OpenAI Client:** Creates `openai.OpenAI` client with `base_url` and `api_key` from settings (line 16)
- **Client Singleton:** Module-level `client` instance reused across calls

**get_llm_client Function (Lines 19-20):** Returns module-level `client` instance.

**`_call_underlying_llm` Function (Lines 23-39):**
- **Parameters:** `prompt: str`, `temperature: float`, `max_tokens: int`, `model: str = None`, `json_mode: bool = False`, `**kwargs`
- **Model Selection:** Uses provided model or `settings.llm_model_name` (line 26)
- **Response Format:** Sets `{"type": "json_object"}` if `json_mode=True`, else `{"type": "text"}` (line 29)
- **API Call:** Calls `client.chat.completions.create()` with model, messages, temperature, max_tokens, response_format (lines 30-36)
- **Response Extraction:** Returns `response.choices[0].message.content` (line 37)
- **Error Handling:** Returns error string on exception (lines 38-39)

**generate_text Function (Lines 42-113):**
- **Parameters:** `prompt: str`, `project_id: str`, `base_temperature: float`, `max_tokens: int = 500`, `model: str = "default_llm"`, `json_mode: bool = False`, `**extra_kwargs`
- **Settings Retrieval:** Gets project-specific execution settings via `get_project_settings(project_id)` (line 55)
- **Temperature Override:** Uses `settings.llm_temperature` instead of `base_temperature` (line 58)
- **Logging:** Logs generation start with project_id, mode, temperature, max_tokens, model, json_mode (lines 60-70)
- **Primary Generation:** Calls `_call_underlying_llm()` with project temperature (lines 73-80)
- **Normal Mode:** Returns raw response immediately if mode is "normal" (lines 82-83)
- **Paranoid Mode:** Performs validation passes if mode is "paranoid" (lines 85-112)
- **Validation Loop:** Runs `settings.validation_passes` iterations (default 3) (line 88)
- **Checker Prompt:** Constructs prompt asking LLM to review and correct draft answer (lines 89-94)
- **Checker Temperature:** Uses `min(temperature, 0.2)` for checker passes (lower temperature for validation) (line 107)
- **Return:** Validated response after all passes complete

**Design Patterns:**
- **Project-Specific Settings:** Temperature and validation passes come from project execution settings
- **Mode-Aware Execution:** Normal mode skips validation, paranoid mode performs multiple passes
- **Error Resilience:** Returns error strings instead of raising exceptions

### RagService (`backend/app/services/rag_service.py`)

**Class Definition (Lines 7-49):** `RagService` provides simple RAG functionality with Qdrant and SentenceTransformer.

**Constructor (Lines 8-26):**
- **Qdrant Client:** Creates `QdrantClient("http://localhost:6333")` (line 10)
- **Embedding Model:** Loads `SentenceTransformer("all-MiniLM-L6-v2")` (384 dimensions) (line 11)
- **Collection Name:** Uses `"cortex_vectors"` collection (line 12)
- **Collection Initialization:** Creates collection if it doesn't exist with COSINE distance (lines 14-22)
- **Error Handling:** Logs warning and continues if Qdrant unavailable (lines 23-26)

**ingest_document Method (Lines 28-41):**
- **Chunking:** Simple overlapping chunker with 500-character chunks, 50-character overlap (lines 31-32)
- **Embedding Generation:** Encodes each chunk via `model.encode(chunk).tolist()` (line 36)
- **Point Creation:** Creates `PointStruct` with UUID ID, vector, payload containing content and metadata (lines 37-38)
- **Upsert:** Uploads points to Qdrant collection (line 41)
- **No Return:** Void method

**search Method (Lines 43-46):**
- **Query Embedding:** Encodes query text to vector (line 44)
- **Vector Search:** Searches Qdrant collection with query vector, returns top `limit` results (line 45)
- **Result Formatting:** Returns list of dicts with `content` and `score` (line 46)
- **Return:** `List[dict]` with content and similarity scores

**Module-Level Instance (Line 49):** `rag_service = RagService()` singleton instance.

### StreamingService (`backend/app/services/streaming_service.py`)

**ConnectionManager Class (Lines 12-62):** Manages WebSocket connections per project.

**Constructor (Lines 15-18):**
- **Connection Storage:** `Dict[str, Set[WebSocket]]` mapping project_id to set of connections (line 17)
- **Lock:** `asyncio.Lock()` for thread-safe connection management (line 18)

**connect Method (Lines 20-27):**
- **WebSocket Acceptance:** Calls `await websocket.accept()` (line 22)
- **Thread Safety:** Uses lock to protect connection dict (line 23)
- **Set Initialization:** Creates set for project_id if not exists (lines 24-25)
- **Connection Addition:** Adds websocket to project's connection set (line 26)
- **Logging:** Logs connection event (line 27)

**disconnect Method (Lines 29-36):**
- **Thread Safety:** Uses lock to protect connection dict (line 31)
- **Connection Removal:** Removes websocket from project's connection set (line 33)
- **Cleanup:** Deletes project entry if no connections remain (lines 34-35)
- **Logging:** Logs disconnection event (line 36)

**broadcast Method (Lines 38-54):**
- **Thread Safety:** Uses lock to protect connection dict (line 40)
- **Early Return:** Returns if no connections for project (lines 41-42)
- **Error Handling:** Tracks disconnected connections, removes them after iteration (lines 44-50)
- **JSON Sending:** Calls `await connection.send_json(event)` for each connection (line 47)
- **Cleanup:** Removes failed connections from set (lines 52-54)

**send_to_connection Method (Lines 56-62):**
- **Direct Send:** Sends event to specific websocket connection
- **Error Handling:** Logs warning and re-raises exception on failure (lines 60-61)

**Module-Level Instance (Line 66):** `connection_manager = ConnectionManager()` singleton instance.

**emit_ingest_event Function (Lines 69-80):**
- **Event Construction:** Creates event dict with type, job data, timestamp, optional error (lines 73-79)
- **Broadcast:** Calls `connection_manager.broadcast(project_id, event)` (line 80)
- **Async:** Uses `asyncio.create_task()` for fire-and-forget emission

**emit_agent_event Function (Lines 83-109):**
- **Event Construction:** Creates event dict with type, timestamp, optional run/step/message/nodeState data, optional error (lines 95-108)
- **Broadcast:** Calls `connection_manager.broadcast(project_id, event)` (line 109)
- **Flexible Data:** Accepts multiple data types (run_data, step_data, message_data, node_state_data)

**emit_workflow_event Function (Lines 112-124):**
- **Event Construction:** Creates event dict with type, timestamp, optional run/nodeState data (lines 116-123)
- **Broadcast:** Calls `connection_manager.broadcast(project_id, event)` (line 124)

### SystemMetricsService (`backend/app/services/system_metrics_service.py`)

**Module-Level Configuration (Lines 26-60):**
- **Default Context Tokens:** `_DEFAULT_CONTEXT_TOTAL_TOKENS = 8_000_000` (line 27)
- **Settings Import:** Attempts to import `get_settings()` with graceful fallback (lines 29-35)
- **Context Token Getter:** `_get_configured_context_total_tokens()` returns configured or default (lines 38-41)
- **Stub Variables:** Module-level `_context_used_tokens` and `_active_agent_runs_stub` (lines 46-47)
- **Stub Setters:** `set_context_usage_stub()` and `set_active_agent_runs_stub()` for testing (lines 50-59)

**GPU Metrics Functions:**
- **`_parse_rocm_smi_output` (Lines 67-127):** Parses `rocm-smi` command output to extract GPU name, VRAM usage, utilization percentage
- **`get_gpu_metrics` (Lines 130-154):** Executes `rocm-smi` command, parses output, returns `Optional[GpuMetrics]` or None if unavailable

**CPU Metrics Functions:**
- **`_get_cpu_stats_psutil` (Lines 162-167):** Uses `psutil` library to get CPU count and load percentage
- **`_get_cpu_stats_stdlib` (Lines 170-180):** Fallback using `os.cpu_count()` and `os.getloadavg()` if psutil unavailable
- **`get_cpu_metrics` (Lines 183-194):** Returns CPU metrics using psutil if available, fallback to stdlib

**Memory Metrics Functions:**
- **`_get_memory_stats_psutil` (Lines 197-202):** Uses `psutil.virtual_memory()` to get total and used memory
- **`_get_memory_stats_proc` (Lines 205-231):** Fallback parsing `/proc/meminfo` on Linux if psutil unavailable
- **`get_memory_metrics` (Lines 234-245):** Returns memory metrics using psutil if available, fallback to /proc

**Context Metrics Functions:**
- **`get_context_metrics` (Lines 253-263):** Returns `ContextMetrics` with total_tokens from config, used_tokens from stub
- **`_get_active_agent_runs` (Lines 266-272):** Returns active agent run count from stub

**Status Aggregation Functions:**
- **`_ratio` (Lines 280-283):** Helper to compute ratio with zero-division protection
- **`_max_status` (Lines 286-288):** Helper to return highest severity status (nominal < warning < critical)
- **`get_system_status` (Lines 291-383):** Aggregates all metrics and classifies overall status:
  - **CPU:** warning >= 75%, critical >= 90%
  - **Memory:** warning >= 75%, critical >= 90%
  - **GPU:** warning >= 75% utilization OR >= 75% VRAM, critical >= 90%
  - **Context:** warning >= 80%, critical >= 95%
  - **Returns:** `SystemStatus` with overall status, reason string, all metrics, active_agent_runs

### QdrantService (`backend/app/services/qdrant_service.py`)

**Class Definition (Lines 26-226):** `QdrantService` manages Qdrant vector database operations for knowledge nodes.

**Constructor (Lines 32-52):**
- **Settings Retrieval:** Gets Qdrant URL from settings (default "http://localhost:6333") (lines 33-34)
- **Client Initialization:** Creates `QdrantClient(url=qdrant_url)` (line 37)
- **Connection Test:** Calls `get_collections()` to verify connection (line 39)
- **Error Handling:** Sets `client = None` if connection fails, logs warning (lines 41-43)
- **Embedding Model:** Loads `SentenceTransformer("all-MiniLM-L6-v2")` (384 dimensions) (lines 46-47)
- **Error Handling:** Sets `embedding_model = None` if model load fails (lines 49-51)

**`_get_collection_name` Method (Lines 54-56):** Generates collection name as `"{collection_type}_{project_id}"` (e.g., "knowledge_project123").

**ensure_collection Method (Lines 58-75):**
- **Availability Check:** Returns False if client unavailable (lines 60-61)
- **Collection Existence:** Checks if collection exists via `client.collection_exists()` (line 66)
- **Collection Creation:** Creates collection with COSINE distance if not exists (lines 67-70)
- **Error Handling:** Returns False on creation failure, logs error (lines 73-74)
- **Return:** Boolean indicating success

**generate_embedding Method (Lines 77-85):**
- **Model Check:** Returns None if embedding model unavailable (lines 79-80)
- **Encoding:** Calls `model.encode(text).tolist()` to generate embedding vector (line 82)
- **Error Handling:** Returns None on encoding failure, logs error (lines 83-84)
- **Return:** `Optional[List[float]]` embedding vector

**upsert_knowledge_node Method (Lines 87-132):**
- **Availability Check:** Returns False if client or model unavailable (lines 97-98)
- **Collection Ensure:** Ensures collection exists (line 100)
- **Text Concatenation:** Combines title, summary, text (limited to 500 chars) for embedding (lines 104-108)
- **Embedding Generation:** Generates embedding via `generate_embedding()` (line 110)
- **Point Creation:** Creates `PointStruct` with node_id, vector, payload containing node metadata (lines 117-127)
- **Upsert:** Uploads point to Qdrant collection (line 128)
- **Error Handling:** Returns False on failure, logs error (lines 130-131)
- **Return:** Boolean indicating success

**delete_knowledge_node Method (Lines 134-146):**
- **Availability Check:** Returns False if client unavailable (line 136)
- **Point Deletion:** Deletes point by ID via `client.delete()` (line 142)
- **Error Handling:** Returns False on failure, logs error (lines 144-145)
- **Return:** Boolean indicating success

**search_knowledge_nodes Method (Lines 148-203):**
- **Availability Check:** Returns empty list if client or model unavailable (lines 157-158)
- **Collection Check:** Returns empty list if collection doesn't exist (lines 162-163)
- **Vector Search:** Generates query embedding, searches collection with optional type filter (lines 168-182)
- **Result Mapping:** Maps search results to dicts with node_id, title, summary, type, score (lines 184-193)
- **Keyword Search Fallback:** Falls back to vector search if keyword-only requested (lines 194-198)
- **Error Handling:** Returns empty list on failure, logs error (lines 201-202)
- **Return:** `List[Dict[str, Any]]` with search results

**hybrid_search Method (Lines 205-222):**
- **Current Implementation:** Uses vector search only (lines 214-222)
- **Future Enhancement:** Placeholder for combining vector and keyword search results
- **Return:** `List[Dict[str, Any]]` search results

**Module-Level Instance (Line 226):** `qdrant_service = QdrantService()` singleton instance.

### QdrantCodeSearchBackend (`backend/app/services/qdrant_code_search.py`)

**Class Definition (Lines 31-255):** `QdrantCodeSearchBackend` implements `CodeSearchBackend` protocol for gap analysis code search.

**Class Constant (Line 36):** `COLLECTION_NAME = "cortex_codebase"` for code chunks.

**Constructor (Lines 38-61):**
- **Client Initialization:** Creates `QdrantClient` from settings URL (line 44)
- **Model Selection:** Attempts code-specific models in order:
  1. `"jinaai/jina-embeddings-v2-base-code"` (768 dimensions) (line 48)
  2. `"microsoft/codebert-base"` (768 dimensions) (line 53)
  3. `"all-MiniLM-L6-v2"` (384 dimensions) fallback (line 58)
- **Collection Ensure:** Calls `_ensure_collection()` (line 61)

**`_ensure_collection` Method (Lines 63-74):**
- **Collection Check:** Verifies collection exists via `get_collections()` (line 67)
- **Collection Creation:** Creates collection with COSINE distance if not exists (lines 68-71)
- **Error Handling:** Logs error on failure (lines 73-74)

**`_chunk_code_ast` Method (Lines 76-109):**
- **Tree-Sitter Check:** Falls back to simple chunking if tree-sitter unavailable (lines 83-85)
- **Language Detection:** Maps file extension to language (py→python, js→javascript, etc.) (lines 89-101)
- **Current Implementation:** Uses simple chunking (tree-sitter bindings require compilation) (line 105)
- **Error Handling:** Falls back to simple chunking on AST parsing failure (lines 107-109)
- **Return:** `List[dict]` with content, line_start, line_end, file_path

**`_chunk_code_simple` Method (Lines 111-168):**
- **Line-Based Parsing:** Splits code into lines, tracks function/class definitions (lines 117-155)
- **Function Detection:** Detects `def` and `async def` keywords (lines 127-139)
- **Class Detection:** Detects `class` keyword (lines 141-153)
- **Chunk Creation:** Creates chunks with content, line ranges, file_path (lines 129-136, 143-150, 158-166)
- **Return:** `List[dict]` with content, line_start, line_end, file_path

**search_related_code Method (Lines 170-213):**
- **Availability Check:** Returns empty list if client unavailable (lines 174-176)
- **Query Construction:** Combines ticket title and description for embedding (line 179)
- **Embedding Generation:** Encodes query text to vector (line 181)
- **Vector Search:** Searches Qdrant with project_id filter (lines 187-195)
- **Result Mapping:** Maps hits to `CodeChunk` objects with file_path, content, similarity (lines 198-207)
- **Error Handling:** Returns empty list on failure, logs error (lines 211-212)
- **Return:** `Sequence[CodeChunk]` ordered by similarity

**ingest_code_file Method (Lines 215-255):**
- **Availability Check:** Returns early if client unavailable (lines 220-221)
- **Chunking:** Calls `_chunk_code_ast()` to chunk code file (line 223)
- **Embedding Generation:** Encodes each chunk to vector (line 229)
- **Point Creation:** Creates points with project_id, file_path, content, line ranges (lines 232-244)
- **Batch Upsert:** Uploads all points to Qdrant collection (lines 250-254)
- **Error Handling:** Logs warnings for individual chunk failures, logs error for batch failure (lines 246-247, 253-254)
- **No Return:** Void method

### ProjectIntelService (`backend/app/services/project_intel_service.py`)

**Module-Level Imports (Lines 23-32):**
- **Optional Dependencies:** Attempts to import `planner_client` and `embedding_client` with graceful fallback (lines 24-32)
- **Type Checking:** Uses `TYPE_CHECKING` guard for `ChatSegment` import (lines 17-20)

**Helper Functions:**
- **`_stable_id` (Lines 38-44):** Generates deterministic 16-character ID from namespace and parts using SHA256 hash
- **`_normalize_text` (Lines 47-48):** Normalizes whitespace in text
- **`_cosine_similarity` (Lines 51-65):** Computes cosine similarity between two embedding vectors
- **`_get_embedding` (Lines 68-85):** Generates embedding via embedding_client if available, returns None otherwise

**Heuristic Rules (Lines 98-115):** `_HEURISTIC_RULES` dict maps idea types to keyword phrases:
- `"feature"`: "we should add", "new feature", "support for", "it would be nice if"
- `"refactor"`: "refactor", "cleanup", "technical debt", "rewrite", "restructure"
- `"experiment"`: "let's try", "experiment", "spike", "prototype", "mvp"
- `"bug"`: "bug", "broken", "doesn't work", "fails when"
- `"ops"`: "alert", "monitoring", "observability", "deployment", "runbook"

**`_apply_heuristics` Function (Lines 118-149):**
- **Text Analysis:** Searches lowercase text for heuristic phrases (lines 119-127)
- **Score Calculation:** Adds 0.2 per matching phrase, clamps to [0, 1] (lines 127, 148)
- **Generic Triggers:** Adds score for generic patterns ("we should", "todo:", etc.) (lines 130-142)
- **Return:** `Optional[_HeuristicMatch]` with score and labels, None if no matches

**extract_idea_candidates_from_segments Function (Lines 152-245):**
- **Deterministic Sorting:** Sorts segments by ID for deterministic processing (line 170)
- **Text Normalization:** Normalizes segment text (line 175)
- **Heuristic Application:** Applies heuristics to extract ideas (lines 179-181)
- **Title/Summary Extraction:** Uses first 12 words for title, first 40 words for summary (lines 183-186)
- **ID Generation:** Uses `_stable_id()` for deterministic candidate IDs (line 192)
- **Candidate Creation:** Creates `IdeaCandidate` with segment metadata (lines 194-204)
- **Planner Refinement:** Optionally refines candidates via planner_client if available (lines 212-243)
- **ID Validation:** Verifies planner returns same IDs, falls back to original on mismatch (lines 223-238)
- **Return:** `List[IdeaCandidate]`

**cluster_ideas Function (Lines 249-354):**
- **Embedding Generation:** Generates embeddings for all candidates if embedding_client available (lines 264-269)
- **Embedding Mode:** Uses cosine similarity clustering if all candidates have embeddings (lines 275-319)
- **Similarity Threshold:** Uses 0.78 threshold for cluster assignment (line 280)
- **Greedy Clustering:** Assigns candidates to best-matching cluster or creates new cluster (lines 282-305)
- **Centroid Update:** Recomputes cluster centroid after adding candidate (lines 307-319)
- **Label-Based Fallback:** Groups by normalized labels if embeddings unavailable (lines 321-345)
- **Deterministic Ordering:** Sorts candidates and clusters by ID for determinism
- **Return:** `List[IdeaCluster]`

**promote_clusters_to_tickets Function (Lines 357-442):**
- **Candidate Lookup:** Uses `candidate_lookup` dict to enrich ticket descriptions (lines 379-383)
- **Title Selection:** Uses highest-confidence candidate as ticket title (lines 387-388)
- **Description Construction:** Combines candidate summaries into description (lines 389-390)
- **ID Generation:** Uses `_stable_id()` for deterministic ticket IDs (line 395)
- **Ticket Creation:** Creates `IdeaTicket` with cluster metadata (lines 397-407)
- **Planner Refinement:** Optionally refines tickets via planner_client if available (lines 410-436)
- **ID Validation:** Verifies planner returns same IDs (lines 421-431)
- **Return:** `List[IdeaTicket]`

### GapAnalysisService (`backend/app/services/gap_analysis_service.py`)

**Protocol Definitions (Lines 19-66):**
- **`IdeaTicket` Protocol (Lines 19-30):** Structural protocol requiring id, project_id, title, description attributes
- **`CodeChunk` Model (Lines 32-39):** Pydantic model with file_path, content, similarity fields
- **`IdeaTicketProvider` Protocol (Lines 42-46):** Requires `list_tickets_for_project()` method
- **`CodeSearchBackend` Protocol (Lines 49-53):** Requires `search_related_code()` method
- **`CoderLLMClient` Protocol (Lines 56-66):** Requires `generate_gap_notes()` method

**GapAnalysisConfig Dataclass (Lines 68-73):**
- **`top_k`:** Number of code chunks to retrieve (default 8)
- **`implemented_threshold`:** Similarity threshold for "implemented" status (default 0.8)
- **`partial_threshold`:** Similarity threshold for "partially_implemented" status (default 0.4)
- **`min_high_matches`:** Minimum high-similarity matches for "implemented" classification (default 2)

**GapAnalysisService Class (Lines 76-168):**
- **Dependencies:** Injected via constructor (ticket_provider, code_search, coder_client, config)
- **Protocol-Based Design:** Uses protocols for dependency injection, enabling test doubles

**generate_gap_report Method (Lines 91-138):**
- **Ticket Retrieval:** Fetches all tickets for project via `ticket_provider` (line 93)
- **Per-Ticket Processing:** Iterates through tickets (lines 98-126)
- **Code Search:** Searches related code via `code_search.search_related_code()` (line 99)
- **Status Classification:** Calls `_classify_status()` to determine gap status and confidence (line 100)
- **Note Generation:** Generates notes via `coder_client.generate_gap_notes()` (lines 109-113)
- **File Extraction:** Extracts unique file paths from code chunks (line 115)
- **Suggestion Creation:** Creates `GapSuggestion` with status, notes, confidence, related_files (lines 117-126)
- **Report Construction:** Creates `GapReport` with project_id, generated_at, suggestions (lines 128-132)
- **Return:** `GapReport`

**`_classify_status` Method (Lines 140-168):**
- **Empty Check:** Returns "unmapped" with 0.0 confidence if no code chunks (lines 141-142)
- **Match Filtering:** Separates implemented_matches (>= implemented_threshold) and partial_matches (between thresholds) (lines 144-147)
- **Implemented Classification:** Returns "implemented" if `min_high_matches` high-similarity matches found (lines 149-153)
- **Partially Implemented Classification:** Returns "partially_implemented" if any matches above partial_threshold (lines 155-163)
- **Unmapped Classification:** Returns "unmapped" with low confidence if only low-similarity matches (lines 165-168)
- **Confidence Calculation:** Uses mean similarity for implemented, normalized top similarity for partially_implemented

**Concrete Adapters:**
- **`ProjectIntelTicketProvider` (Lines 174-177):** Implements `IdeaTicketProvider` using `project_intel_repo.list_tickets()`
- **`LLMCoderClient` (Lines 180-206):** Implements `CoderLLMClient` using `llm_service.generate_text()` with gap analysis prompt
- **`NullTicketProvider` (Lines 209-212):** Null implementation returning empty list
- **`NullCodeSearchBackend` (Lines 215-218):** Null implementation returning empty list
- **`NullCoderLLMClient` (Lines 221-236):** Null implementation returning status-based messages

**Module-Level Service Management:**
- **`_default_service` (Line 239):** Module-level service instance
- **`configure_gap_analysis_service` (Lines 242-248):** Sets module-level service instance
- **`get_gap_analysis_service` (Lines 251-275):** Returns configured service or initializes with real adapters:
  - Attempts to use `QdrantCodeSearchBackend` with `ProjectIntelTicketProvider` and `LLMCoderClient`
  - Falls back to null adapters on initialization failure
- **`generate_gap_report` (Lines 278-283):** Convenience wrapper calling service method

### WorkflowGraphCompiler (`backend/app/services/workflow_compiler.py`)

**WorkflowState TypedDict (Lines 13-22):** Defines state structure with run_id, project_id, input, output, messages, current_node fields.

**Class Definition (Lines 24-65):** `WorkflowGraphCompiler` compiles `WorkflowGraph` domain models to LangGraph `StateGraph`.

**compile Method (Lines 27-52):**
- **Graph Creation:** Creates `StateGraph(WorkflowState)` (line 29)
- **Node Addition:** Adds nodes from workflow_graph.nodes via `graph.add_node(node.id, node_function)` (lines 32-33)
- **Edge Processing:** Processes edges to find entry point and end connections (lines 36-43)
- **Entry Point:** Sets entry point from edge with source "__start__" or first node (lines 45-50)
- **Compilation:** Returns compiled graph via `graph.compile()` (line 52)
- **Return:** Compiled LangGraph `StateGraph`

**`_create_node_function` Method (Lines 54-65):**
- **Placeholder Implementation:** Creates async function that logs execution and returns state update (lines 57-63)
- **State Update:** Returns dict with output and current_node fields (line 63)
- **Note:** Actual execution logic handled by `WorkflowService.execute_workflow_run()`

### SystemService (`backend/app/services/system_service.py`)

**Class Definition (Lines 8-22):** `SystemService` provides simple system status stub.

**get_status Method (Lines 13-19):**
- **Static Response:** Returns deterministic `SystemStatus` with `NOMINAL` status (line 16)
- **Message:** Returns "Cortex backend stub is running." (line 17)
- **Timestamp:** Uses `datetime.utcnow()` (line 18)
- **Note:** This is a stub; real implementation uses `system_metrics_service.get_system_status()`

**Module-Level Instance (Line 22):** `system_service = SystemService()` singleton instance.

---

## API Contract & Endpoints Deep Dive

The API contract defines 14 route modules with 50+ endpoints covering all domain operations. All endpoints use JSON over HTTP with token-based authentication (except `/api/token`). Real-time updates delivered via WebSocket or Server-Sent Events (SSE).

### Authentication Endpoints (`backend/app/api/routes/auth.py`)

**POST /api/token** (Lines 12-20):
- **Purpose:** OAuth2 password flow token generation
- **Request:** `OAuth2PasswordRequestForm` (username, password via form data)
- **Response:** `{"access_token": str, "token_type": "bearer"}`
- **Auth Required:** No (public endpoint)
- **Token Expiry:** `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 minutes, line 18)
- **Implementation:** `create_access_token(data={"sub": form_data.username})` creates JWT with username as subject
- **Security Note:** Currently accepts any username without credential verification (line 16 comment indicates placeholder)

### Projects Endpoints (`backend/app/api/routes/projects.py`)

**GET /api/projects** (Lines 18-24):
- **Purpose:** List projects with cursor-based pagination
- **Query Parameters:** `cursor?: string`, `limit: int` (default 50, range 1-100)
- **Response:** `PaginatedResponse[CortexProject]`
- **Service:** `ProjectService.list_projects(cursor, limit)`
- **Auth Required:** Yes (via `auth_deps` in main.py)

**POST /api/projects** (Lines 27-32):
- **Purpose:** Create new project
- **Request Body:** `CreateProjectRequest` (name, slug?, description?)
- **Response:** `CortexProject` (status 201)
- **Service:** `ProjectService.create_project(body)`
- **Validation:** Pydantic model validation on request body

**GET /api/projects/{project_id}** (Lines 35-40):
- **Purpose:** Get single project by ID
- **Path Parameter:** `project_id: str`
- **Response:** `CortexProject`
- **Service:** `ProjectService.get_project(project_id)`
- **Error:** 404 if not found (handled by service)

**PATCH /api/projects/{project_id}** (Lines 43-49):
- **Purpose:** Partial update of project
- **Path Parameter:** `project_id: str`
- **Request Body:** `UpdateProjectRequest` (all fields optional)
- **Response:** `CortexProject`
- **Service:** `ProjectService.update_project(project_id, body)`
- **Update Strategy:** Partial updates via Pydantic model `copy(update=...)`

**DELETE /api/projects/{project_id}** (Lines 52-57):
- **Purpose:** Delete/archive project
- **Path Parameter:** `project_id: str`
- **Response:** `DeleteProjectResponse` (success boolean)
- **Service:** `ProjectService.delete_project(project_id)`
- **Cascade:** Foreign key constraints handle related data cleanup

### Ingest Endpoints (`backend/app/api/routes/ingest.py`)

**GET /api/projects/{project_id}/ingest/jobs** (Lines 15-31):
- **Purpose:** List ingest jobs with filtering
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50), `status?: string`, `stage?: string`, `source_id?: string`
- **Response:** `PaginatedResponse[IngestJob]`
- **Service:** `ingest_service.list_jobs(project_id, cursor, limit, status, stage, source_id)`
- **Filtering:** Supports status, stage, and source_id filters for Ingest Station UI

**GET /api/projects/{project_id}/ingest/jobs/{job_id}** (Lines 34-39):
- **Purpose:** Get single ingest job
- **Path Parameters:** `project_id: str`, `job_id: str`
- **Response:** `IngestJob`
- **Service:** `ingest_service.get_job(job_id)`
- **Validation:** Verifies `job.project_id == project_id` (line 37), returns 404 if mismatch

**POST /api/projects/{project_id}/ingest/jobs** (Lines 42-50):
- **Purpose:** Create new ingest job
- **Path Parameter:** `project_id: str`
- **Request Body:** `IngestRequest` (requires `source_path: str`)
- **Response:** `IngestJob` (status 201)
- **Service:** `ingest_service.create_job(project_id, request)` then `process_job(job.id)` in background
- **Background Processing:** `BackgroundTasks.add_task` queues job processing (line 49)
- **Validation:** Raises 400 if `source_path` missing (line 46-47)

**POST /api/projects/{project_id}/ingest/jobs/{job_id}/cancel** (Lines 53-66):
- **Purpose:** Cancel running ingest job
- **Path Parameters:** `project_id: str`, `job_id: str`
- **Response:** `IngestJob` (updated status)
- **Service:** `ingest_service.cancel_job(job_id)`
- **Validation:** Verifies job exists and belongs to project (lines 59-61)
- **Status Check:** Only cancellable if status is `QUEUED` or `RUNNING` (line 63), returns 400 otherwise

**DELETE /api/projects/{project_id}/ingest/jobs/{job_id}** (Lines 69-79):
- **Purpose:** Delete ingest job
- **Path Parameters:** `project_id: str`, `job_id: str`
- **Response:** 204 No Content
- **Service:** `ingest_service.delete_job(job_id)`
- **Validation:** Verifies job exists and belongs to project (lines 71-73)
- **Status Check:** Cannot delete if status is `RUNNING` (line 75-76), must cancel first

**POST /api/projects/{project_id}/ingest/upload** (Lines 82-94):
- **Purpose:** Upload file and create ingest job
- **Path Parameter:** `project_id: str`
- **Request:** `multipart/form-data` with `file: UploadFile`
- **Response:** `{"filename": str, "job_id": str}`
- **File Handling:** Saves to `temp_uploads/` directory (lines 84-89)
- **Job Creation:** Creates `IngestRequest` with file path, queues processing (lines 91-92)

### Agents Endpoints (`backend/app/api/routes/agents.py`)

**GET /api/profiles** (Lines 25-27):
- **Purpose:** List available agent profiles
- **Response:** `List[AgentProfile]`
- **Service:** `agent_service.list_agents()`
- **No Auth:** Public endpoint (no project scoping)

**GET /api/profiles/{agent_id}** (Lines 30-35):
- **Purpose:** Get single agent profile
- **Path Parameter:** `agent_id: str`
- **Response:** `AgentProfile`
- **Service:** `agent_service.get_agent(agent_id)`
- **Error:** 404 if agent not found (line 33-34)

**GET /api/projects/{project_id}/agent-runs** (Lines 38-41):
- **Purpose:** List agent runs for project
- **Path Parameter:** `project_id: str`
- **Response:** `List[AgentRun]` (not paginated, returns list directly)
- **Service:** `agent_service.list_runs(project_id)`
- **Note:** Returns list directly, not `PaginatedResponse` (line 41 handles both list and paginated)

**GET /api/projects/{project_id}/agent-runs/{run_id}** (Lines 44-49):
- **Purpose:** Get single agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `AgentRun`
- **Service:** `agent_service.get_run(run_id)`
- **Validation:** Verifies `run.project_id == project_id` (line 47-48)

**POST /api/projects/{project_id}/agent-runs** (Lines 52-67):
- **Purpose:** Start new agent run
- **Path Parameter:** `project_id: str`
- **Request Body:** `AgentRunRequest` (agent_id, project_id, input_prompt, context_item_ids?)
- **Response:** `AgentRun` (created run record)
- **Service:** `agent_service.create_run_record(request)` then `execute_run(run.id)` in background
- **Validation:** Verifies `request.project_id == project_id` (line 54-55), verifies agent exists (lines 57-59)
- **Execution:** Background task offloads LangGraph execution (line 65)

**GET /api/projects/{project_id}/agent-runs/{run_id}/steps** (Lines 70-85):
- **Purpose:** List steps for agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50)
- **Response:** `PaginatedResponse[AgentStep]`
- **Service:** `agent_service.list_steps(run_id, cursor, limit)`
- **Validation:** Verifies run exists and belongs to project (lines 81-83)

**GET /api/projects/{project_id}/agent-runs/{run_id}/messages** (Lines 88-103):
- **Purpose:** List messages for agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50)
- **Response:** `PaginatedResponse[AgentMessage]`
- **Service:** `agent_service.list_messages(run_id, cursor, limit)`
- **Chronological Order:** Messages ordered by `created_at` via index

**POST /api/projects/{project_id}/agent-runs/{run_id}/messages** (Lines 106-126):
- **Purpose:** Append user message to agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Request Body:** `AppendMessageRequest` (content, role?, context_item_ids?)
- **Response:** `AgentMessage` (status 201)
- **Service:** `agent_service.append_message(run_id, request)`
- **Status Handling:** If run is `COMPLETED`, restarts to `PENDING` (lines 121-124)
- **Validation:** Verifies run exists and belongs to project (lines 117-119)

**GET /api/projects/{project_id}/agent-runs/{run_id}/node-states** (Lines 129-142):
- **Purpose:** List node states for agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `List[AgentNodeState]` (not paginated)
- **Service:** `agent_service.list_node_states(run_id)`
- **Node States:** LangGraph node execution status, progress, messages

**POST /api/projects/{project_id}/agent-runs/{run_id}/cancel** (Lines 145-157):
- **Purpose:** Cancel agent run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `AgentRun` (updated status)
- **Service:** `agent_service.cancel_run(run_id)`
- **Validation:** Verifies run exists and belongs to project (lines 150-152)
- **Status Check:** Cannot cancel if already `COMPLETED`, `FAILED`, or `CANCELLED` (line 154-155)

**GET /api/projects/{project_id}/agent-runs/{run_id}/stream** (Lines 160-172):
- **Purpose:** Stream agent run events via SSE
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `text/event-stream` (Server-Sent Events)
- **Streaming:** Uses LangGraph `astream_events()` to emit events (lines 167-169)
- **Event Format:** `data: {json.dumps(event)}\n\n` (line 170)
- **Validation:** Verifies run exists and belongs to project (lines 162-164)

### Workflows Endpoints (`backend/app/api/routes/workflows.py`)

**GET /api/projects/{project_id}/workflows/graphs** (Lines 25-31):
- **Purpose:** List workflow graphs for project
- **Path Parameter:** `project_id: str`
- **Response:** `List[WorkflowGraph]`
- **Service:** `workflow_service.list_graphs(project_id)`

**GET /api/projects/{project_id}/workflows/graphs/{workflow_id}** (Lines 34-43):
- **Purpose:** Get workflow graph by ID
- **Path Parameters:** `project_id: str`, `workflow_id: str`
- **Response:** `WorkflowGraph`
- **Service:** `workflow_service.get_graph(workflow_id)`
- **Error:** 404 if not found (lines 41-42)

**POST /api/projects/{project_id}/workflows/runs** (Lines 46-65):
- **Purpose:** Create workflow run
- **Path Parameter:** `project_id: str`
- **Request Body:** `CreateWorkflowRunRequest` (workflow_id, input_data?)
- **Response:** `WorkflowRun` (status 201)
- **Service:** `workflow_service.create_run(project_id, workflow_id, input_data)` then `execute_workflow_run(run.id)` in background
- **Validation:** Verifies workflow exists (lines 52-54)
- **Execution:** Background task schedules LangGraph execution (line 63)

**GET /api/projects/{project_id}/workflows/runs** (Lines 68-74):
- **Purpose:** List workflow runs for project
- **Path Parameter:** `project_id: str`
- **Query Parameter:** `workflow_id?: str` (optional filter)
- **Response:** `List[WorkflowRun]`
- **Service:** `workflow_service.list_runs(project_id, workflow_id)`

**GET /api/projects/{project_id}/workflows/runs/{run_id}** (Lines 77-84):
- **Purpose:** Get workflow run by ID
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `WorkflowRun`
- **Service:** `workflow_service.get_run(run_id)`
- **Error:** 404 if not found (lines 82-83)

**POST /api/projects/{project_id}/workflows/runs/{run_id}/execute** (Lines 87-125):
- **Purpose:** Execute workflow run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Request Body:** `ExecuteWorkflowRunRequest?` (input_data?)
- **Response:** `WorkflowRun` (status 202 Accepted)
- **Service:** `workflow_service.execute_workflow_run(run_id)` in background
- **Validation:** Cannot execute if already `RUNNING` (lines 103-104) or `COMPLETED` (lines 106-107)
- **Input Update:** Updates `input_json` if provided (lines 110-117)
- **Execution:** Uses `BackgroundTasks` if available, else `asyncio.create_task` (lines 120-123)

**POST /api/projects/{project_id}/workflows/runs/{run_id}/cancel** (Lines 128-139):
- **Purpose:** Cancel workflow run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `WorkflowRun` (updated status)
- **Service:** `workflow_service.cancel_workflow_run(run_id)`
- **Error Handling:** Catches `ValueError` and returns 400 (lines 137-139)

**POST /api/projects/{project_id}/workflows/runs/{run_id}/pause** (Lines 142-153):
- **Purpose:** Pause workflow run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `WorkflowRun` (status updated to PAUSED)
- **Service:** `workflow_service.pause_workflow_run(run_id)`
- **Checkpoint:** Saves checkpoint state for resume capability
- **Error Handling:** Catches `ValueError` and returns 400 (lines 151-153)

**POST /api/projects/{project_id}/workflows/runs/{run_id}/resume** (Lines 156-172):
- **Purpose:** Resume paused workflow run
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Request Body:** `ResumeWorkflowRunRequest?` (checkpoint_id?)
- **Response:** `WorkflowRun` (status 202 Accepted)
- **Service:** `workflow_service.resume_workflow_run(run_id)`
- **Checkpoint:** Uses checkpoint_id if provided, else latest checkpoint
- **Error Handling:** Catches `ValueError` and returns 400 (lines 170-172)

**GET /api/projects/{project_id}/workflows/runs/{run_id}/status** (Lines 175-184):
- **Purpose:** Get workflow run execution status
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Response:** `dict` (execution status details)
- **Service:** `workflow_service.get_execution_status(run_id)`
- **Status Details:** Includes node states, progress, messages, errors
- **Error Handling:** Catches `ValueError` and returns 404 (lines 182-184)

### Roadmap Endpoints (`backend/app/api/routes/roadmap.py`)

**GET /api/projects/{project_id}/roadmap/nodes** (Lines 17-31):
- **Purpose:** List roadmap nodes with filtering
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50), `status?: string`, `lane_id?: string`
- **Response:** `PaginatedResponse[RoadmapNode]`
- **Service:** `roadmap_service.list_nodes(project_id, cursor, limit, status, lane_id)`
- **Filtering:** Supports status and lane_id filters for roadmap UI

**POST /api/projects/{project_id}/roadmap/nodes** (Lines 34-44):
- **Purpose:** Create roadmap node
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (node_data with label, description, status, priority, dates, etc.)
- **Response:** `RoadmapNode` (status 201)
- **Service:** `roadmap_service.create_node(project_id, node_data)`
- **Error Handling:** Catches `ValueError` and returns 400 (lines 42-44)

**GET /api/projects/{project_id}/roadmap/nodes/{node_id}** (Lines 47-55):
- **Purpose:** Get roadmap node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Response:** `RoadmapNode`
- **Service:** `roadmap_service.get_node(project_id, node_id)`
- **Error:** 404 if not found (lines 53-54)

**PATCH /api/projects/{project_id}/roadmap/nodes/{node_id}** (Lines 58-71):
- **Purpose:** Update roadmap node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Request Body:** `dict` (partial updates)
- **Response:** `RoadmapNode`
- **Service:** `roadmap_service.update_node(project_id, node_id, updates)`
- **Error Handling:** 404 if not found, 400 for validation errors (lines 68-71)

**DELETE /api/projects/{project_id}/roadmap/nodes/{node_id}** (Lines 74-83):
- **Purpose:** Delete roadmap node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Response:** `{"success": true}` (status 200)
- **Service:** `roadmap_service.delete_node(project_id, node_id)`
- **Cascade:** Deletes dependent edges automatically

**GET /api/projects/{project_id}/roadmap/edges** (Lines 86-92):
- **Purpose:** List roadmap edges
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50)
- **Response:** `PaginatedResponse[RoadmapEdge]`
- **Service:** `roadmap_service.list_edges(project_id, cursor, limit)`

**POST /api/projects/{project_id}/roadmap/edges** (Lines 95-106):
- **Purpose:** Create roadmap edge
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (edge_data with from_node_id, to_node_id, kind, label?)
- **Response:** `RoadmapEdge` (status 201)
- **Service:** `roadmap_service.create_edge(project_id, edge_data)`
- **Error Handling:** 409 if edge already exists, 400 for validation errors (lines 104-105)

**DELETE /api/projects/{project_id}/roadmap/edges/{edge_id}** (Lines 109-115):
- **Purpose:** Delete roadmap edge
- **Path Parameters:** `project_id: str`, `edge_id: str`
- **Response:** `{"success": true}` (status 200)
- **Service:** `roadmap_service.delete_edge(project_id, edge_id)`

**GET /api/projects/{project_id}/roadmap** (Lines 118-122):
- **Purpose:** Get complete roadmap graph
- **Path Parameter:** `project_id: str`
- **Response:** `RoadmapGraph` (nodes + edges)
- **Service:** `roadmap_service.get_graph(project_id)`
- **Graph Structure:** Returns all nodes and edges as single graph object

### Knowledge Graph Endpoints (`backend/app/api/routes/knowledge.py`)

**GET /api/projects/{project_id}/knowledge-graph** (Lines 17-25):
- **Purpose:** Get knowledge graph snapshot
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `view?: string`, `focus_node_id?: string`
- **Response:** `KnowledgeGraph` (nodes + edges)
- **Service:** `knowledge_service.get_graph(project_id, view, focus_node_id)`
- **View Filtering:** Supports different graph views (full, focused, etc.)

**GET /api/projects/{project_id}/knowledge-graph/nodes/{node_id}** (Lines 28-40):
- **Purpose:** Get single knowledge node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Response:** `KnowledgeNode`
- **Service:** `knowledge_service.get_node(project_id, node_id)`
- **Error:** 404 if not found (lines 38-39)

**GET /api/projects/{project_id}/knowledge-graph/nodes/{node_id}/neighbors** (Lines 43-55):
- **Purpose:** Get neighbors for a node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Response:** `dict` (neighbors structure)
- **Service:** `knowledge_service.get_node_neighbors(project_id, node_id)`
- **Error Handling:** Catches `ValueError` and returns 404 (lines 54-55)

**POST /api/projects/{project_id}/knowledge-graph/nodes** (Lines 58-71):
- **Purpose:** Create knowledge node
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (node_data with title, content, type, embedding?, etc.)
- **Response:** `KnowledgeNode` (status 201)
- **Service:** `knowledge_service.create_node(project_id, node_data)`
- **Error Handling:** Catches `ValueError` and returns 400 (lines 70-71)

**PATCH /api/projects/{project_id}/knowledge-graph/nodes/{node_id}** (Lines 74-87):
- **Purpose:** Update knowledge node
- **Path Parameters:** `project_id: str`, `node_id: str`
- **Request Body:** `dict` (partial updates)
- **Response:** `KnowledgeNode`
- **Service:** `knowledge_service.update_node(project_id, node_id, updates)`
- **Error Handling:** Catches `ValueError` and returns 404 (lines 86-87)

**POST /api/projects/{project_id}/knowledge-graph/edges** (Lines 90-104):
- **Purpose:** Create knowledge edge
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (edge_data with source, target, type, weight?, label?)
- **Response:** `KnowledgeEdge` (status 201)
- **Service:** `knowledge_service.create_edge(project_id, edge_data)`
- **Error Handling:** 409 if edge already exists, 400 for validation errors (lines 102-103)

**DELETE /api/projects/{project_id}/knowledge-graph/edges/{edge_id}** (Lines 107-115):
- **Purpose:** Delete knowledge edge
- **Path Parameters:** `project_id: str`, `edge_id: str`
- **Response:** `{"success": true}` (status 200)
- **Service:** `knowledge_service.delete_edge(project_id, edge_id)`

**POST /api/projects/{project_id}/knowledge/search** (Lines 118-125):
- **Purpose:** Search knowledge nodes
- **Path Parameter:** `project_id: str`
- **Request Body:** `KnowledgeSearchRequest` (query, limit?, filters?)
- **Response:** `List[KnowledgeNode]` (search results)
- **Service:** `knowledge_service.search(project_id, request)`
- **Search:** Vector similarity search via Qdrant, returns ranked results

### Context Endpoints (`backend/app/api/routes/context.py`)

**GET /api/projects/{project_id}/context** (Lines 17-19):
- **Purpose:** Get context budget and items
- **Path Parameter:** `project_id: str`
- **Response:** `ContextBudget` (total_tokens, used_tokens, max_tokens, items)
- **Service:** `context_service.get_budget(project_id)`
- **Budget Calculation:** Sums token counts from all context items

**POST /api/projects/{project_id}/context/items** (Lines 22-32):
- **Purpose:** Add context items
- **Path Parameter:** `project_id: str`
- **Request Body:** `AddContextItemsRequest` (items: List[ContextItem])
- **Response:** `AddContextItemsResponse` (added items, budget)
- **Service:** `context_service.add_items(project_id, request)`
- **Budget Check:** Validates total tokens don't exceed max_tokens
- **Error Handling:** Catches `ValueError` (budget overflow) and returns 400 (lines 31-32)

**PATCH /api/projects/{project_id}/context/items/{context_item_id}** (Lines 35-53):
- **Purpose:** Update context item
- **Path Parameters:** `project_id: str`, `context_item_id: str`
- **Request Body:** `dict` (partial update: pinned?, tokens?)
- **Response:** `ContextItem`
- **Service:** `context_service.update_item(project_id, context_item_id, pinned, tokens)`
- **Update Fields:** Only `pinned` and `tokens` supported (lines 44-45)
- **Error Handling:** Catches `ValueError` and returns 404 (lines 52-53)

**DELETE /api/projects/{project_id}/context/items/{context_item_id}** (Lines 56-68):
- **Purpose:** Remove context item
- **Path Parameters:** `project_id: str`, `context_item_id: str`
- **Response:** `ContextBudget` (updated budget)
- **Service:** `context_service.remove_item(project_id, context_item_id)`
- **Budget Update:** Returns updated budget after removal
- **Error Handling:** Catches `ValueError` and returns 404 (lines 67-68)

**GET /api/projects/{project_id}/context/items** (Lines 71-73):
- **Purpose:** List all context items
- **Path Parameter:** `project_id: str`
- **Response:** `List[ContextItem]`
- **Service:** `context_service.list_items(project_id)`
- **Note:** Alternative to getting items via `/context` endpoint

### Ideas Endpoints (`backend/app/api/routes/ideas.py`)

**GET /api/projects/{project_id}/ideas/candidates** (Lines 19-33):
- **Purpose:** List idea candidates
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50), `status?: string`, `type?: string`
- **Response:** `PaginatedResponse[IdeaCandidate]`
- **Service:** `idea_service.list_candidates(project_id, cursor, limit, status, type)`
- **Filtering:** Supports status and type filters

**POST /api/projects/{project_id}/ideas/candidates** (Lines 36-46):
- **Purpose:** Create idea candidate
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (candidate_data)
- **Response:** `IdeaCandidate` (status 201)
- **Service:** `idea_service.create_candidate(project_id, candidate_data)`

**PATCH /api/projects/{project_id}/ideas/candidates/{idea_id}** (Lines 49-60):
- **Purpose:** Update idea candidate
- **Path Parameters:** `project_id: str`, `idea_id: str`
- **Request Body:** `dict` (partial updates)
- **Response:** `IdeaCandidate`
- **Service:** `idea_service.update_candidate(project_id, idea_id, updates)`
- **Error Handling:** Catches `ValueError` and returns 404 (lines 59-60)

**GET /api/projects/{project_id}/ideas/clusters** (Lines 64-70):
- **Purpose:** List idea clusters
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50)
- **Response:** `PaginatedResponse[IdeaCluster]`
- **Service:** `idea_service.list_clusters(project_id, cursor, limit)`

**POST /api/projects/{project_id}/ideas/clusters** (Lines 73-80):
- **Purpose:** Create idea cluster
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (cluster_data)
- **Response:** `IdeaCluster` (status 201)
- **Service:** `idea_service.create_cluster(project_id, cluster_data)`

**GET /api/projects/{project_id}/ideas/tickets** (Lines 84-96):
- **Purpose:** List idea tickets
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50), `status?: string`
- **Response:** `PaginatedResponse[IdeaTicket]`
- **Service:** `idea_service.list_tickets(project_id, cursor, limit, status)`
- **Filtering:** Supports status filter for Mission Control board

**POST /api/projects/{project_id}/ideas/tickets** (Lines 99-109):
- **Purpose:** Create ticket from idea
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (ticket_data)
- **Response:** `IdeaTicket` (status 201)
- **Service:** `idea_service.create_ticket(project_id, ticket_data)`

**GET /api/projects/{project_id}/tasks** (Lines 113-127):
- **Purpose:** List mission control tasks
- **Path Parameter:** `project_id: str`
- **Query Parameters:** `cursor?: string`, `limit: int` (1-100, default 50), `column?: string`, `origin?: string`
- **Response:** `PaginatedResponse[MissionControlTask]`
- **Service:** `idea_service.list_tasks(project_id, cursor, limit, column, origin)`
- **Filtering:** Supports column (backlog/todo/in_progress/done) and origin filters

**POST /api/projects/{project_id}/tasks** (Lines 130-140):
- **Purpose:** Create mission control task
- **Path Parameter:** `project_id: str`
- **Request Body:** `dict` (task_data)
- **Response:** `MissionControlTask` (status 201)
- **Service:** `idea_service.create_task(project_id, task_data)`

**PATCH /api/projects/{project_id}/tasks/{task_id}** (Lines 143-154):
- **Purpose:** Update mission control task
- **Path Parameters:** `project_id: str`, `task_id: str`
- **Request Body:** `dict` (partial updates)
- **Response:** `MissionControlTask`
- **Service:** `idea_service.update_task(project_id, task_id, updates)`
- **Error Handling:** Catches `ValueError` and returns 404 (lines 153-154)

### Gap Analysis Endpoints (`backend/app/api/routes/gap_analysis.py`)

**POST /api/projects/{project_id}/gap-analysis/run** (Lines 21-32):
- **Purpose:** Trigger new gap analysis run
- **Path Parameter:** `project_id: str`
- **Response:** `GapReport` (generated report)
- **Service:** `GapAnalysisService.generate_gap_report(project_id)` then `save_gap_report(report)`
- **Process:** Fetches tickets, searches code, classifies status, generates suggestions
- **Persistence:** Report saved to database immediately

**GET /api/projects/{project_id}/gap-analysis/latest** (Lines 35-49):
- **Purpose:** Get latest gap analysis report
- **Path Parameter:** `project_id: str`
- **Response:** `GapReport`
- **Service:** `GapAnalysisRepo.get_latest_gap_report(project_id)`
- **Error:** 404 if no report exists (lines 44-48)

**GET /api/projects/{project_id}/gap-analysis/history** (Lines 52-62):
- **Purpose:** List historical gap analysis reports
- **Path Parameter:** `project_id: str`
- **Query Parameter:** `limit: int` (default 20)
- **Response:** `List[GapReport]` (newest first)
- **Service:** `GapAnalysisRepo.list_gap_reports(project_id, limit)`
- **Ordering:** Returns newest reports first

### Project Intel Endpoints (`backend/app/api/routes/project_intel.py`)

**POST /api/projects/{project_id}/ideas/rebuild** (Lines 75-127):
- **Purpose:** Rebuild project ideas from chat segments
- **Path Parameter:** `project_id: str`
- **Response:** `dict` (candidate_ids, cluster_ids, ticket_ids) (status 202 Accepted)
- **Process:** Extracts candidates from chat segments, clusters ideas, promotes to tickets
- **Service Functions:** `extract_idea_candidates_from_segments()`, `cluster_ideas()`, `promote_clusters_to_tickets()`
- **Persistence:** Saves candidates, clusters, tickets to repository
- **Idempotent:** Deterministic ID generation ensures idempotency
- **Error:** 501 if chat segment repository not configured (lines 87-91)

**GET /api/projects/{project_id}/ideas/candidates** (Lines 130-135):
- **Purpose:** Get project idea candidates
- **Path Parameter:** `project_id: str`
- **Response:** `List[IdeaCandidate]`
- **Service:** `project_intel_repo.list_candidates(project_id)`
- **Note:** Duplicate of `/ideas/candidates` endpoint, different implementation

**GET /api/projects/{project_id}/ideas/clusters** (Lines 138-143):
- **Purpose:** Get project idea clusters
- **Path Parameter:** `project_id: str`
- **Response:** `List[IdeaCluster]`
- **Service:** `project_intel_repo.list_clusters(project_id)`
- **Note:** Duplicate of `/ideas/clusters` endpoint, different implementation

**GET /api/projects/{project_id}/ideas/tickets** (Lines 146-151):
- **Purpose:** Get project idea tickets
- **Path Parameter:** `project_id: str`
- **Response:** `List[IdeaTicket]`
- **Service:** `project_intel_repo.list_tickets(project_id)`
- **Note:** Duplicate of `/ideas/tickets` endpoint, different implementation

**PATCH /api/projects/{project_id}/ideas/tickets/{ticket_id}** (Lines 154-190):
- **Purpose:** Update idea ticket status/priority
- **Path Parameters:** `project_id: str`, `ticket_id: str`
- **Request Body:** `TicketUpdateRequest` (status?, priority?)
- **Response:** `IdeaTicket`
- **Service:** `project_intel_repo.update_ticket_status(ticket_id, status, priority)`
- **Validation:** Requires at least one field (status or priority) (lines 166-170)
- **Error Handling:** 404 if ticket not found, 500 if update fails (lines 184-188)

### Mode Endpoints (`backend/app/api/routes/mode.py`)

**GET /api/projects/{project_id}/mode** (Lines 22-31):
- **Purpose:** Get project execution settings
- **Path Parameter:** `project_id: str`
- **Response:** `ProjectExecutionSettings` (mode, llm_temperature, validation_passes, max_parallel_tools)
- **Service:** `mode_repo.get_project_settings(project_id)`
- **Defaults:** Returns default settings if not configured

**PATCH /api/projects/{project_id}/mode** (Lines 34-90):
- **Purpose:** Update project execution settings
- **Path Parameter:** `project_id: str`
- **Request Body:** `ProjectExecutionSettingsUpdateRequest` (mode?, llm_temperature?, validation_passes?, max_parallel_tools?)
- **Response:** `ProjectExecutionSettings`
- **Service:** `mode_repo.set_project_settings(updated)`
- **Validation:** Requires at least one field (lines 51-62)
- **Constraints:** `llm_temperature` 0.0-2.0, `validation_passes` 1-10, `max_parallel_tools` 1-64
- **Logging:** Logs update with all settings (lines 79-88)

### System Endpoints (`backend/app/api/routes/system.py`)

**GET /api/system/health** (Lines 11-13):
- **Purpose:** Basic liveness probe
- **Response:** `MessageResponse` (message: "ok")
- **No Auth:** Public endpoint for health checks
- **Use Case:** Kubernetes/Docker health checks

**GET /api/system/status** (Lines 16-32):
- **Purpose:** Get system status snapshot
- **Response:** `SystemStatus` (gpu_metrics, cpu_metrics, memory_metrics, context_metrics, overall_status)
- **Service:** `get_system_status()` (synchronous metrics collection)
- **Polling:** Frontend polls this endpoint periodically
- **Metrics:** GPU (if available), CPU, memory, context token usage, active agent runs

### Streaming Endpoints (`backend/app/api/routes/streaming.py`)

**WebSocket /api/stream/projects/{project_id}/ingest/{job_id}** (Lines 26-79):
- **Purpose:** Stream ingest job events via WebSocket
- **Path Parameters:** `project_id: str`, `job_id: str`
- **Connection:** `connection_manager.connect(websocket, project_id)` (line 29)
- **Initial State:** Sends `ingest.job.created` event with job data (line 45)
- **Polling:** Polls job status every 1 second (line 50)
- **Events:** Emits `ingest.job.{status}` events on status change (line 58)
- **Termination:** Closes on `completed`, `failed`, or `cancelled` status (line 61)
- **Error Handling:** Sends error JSON and closes connection on exceptions (lines 69-77)
- **Disconnect:** Cleans up connection on disconnect (line 79)

**SSE /api/stream/projects/{project_id}/ingest/{job_id}/events** (Lines 82-111):
- **Purpose:** Stream ingest job events via Server-Sent Events
- **Path Parameters:** `project_id: str`, `job_id: str`
- **Response:** `text/event-stream`
- **Format:** `event: {type}\n` `data: {json}\n\n` (lines 90-91, 103-104)
- **Polling:** Polls job status every 1 second (line 95)
- **Events:** Same as WebSocket endpoint
- **Termination:** Breaks loop on terminal status (line 106)

**WebSocket /api/stream/projects/{project_id}/agent-runs/{run_id}** (Lines 117-185):
- **Purpose:** Stream agent run events via WebSocket
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Connection:** `connection_manager.connect(websocket, project_id)` (line 120)
- **Initial State:** Sends `agent.run.created` event (line 133)
- **Polling:** Polls run status every 1 second (line 138)
- **Run Events:** Emits `agent.run.{status}` events (line 146)
- **Step Events:** Sends last 5 steps as `agent.step.updated` (lines 155-158)
- **Message Events:** Sends last 5 messages as `agent.message.appended` (lines 161-164)
- **Node State Events:** Sends all node states as `workflow.node_state.updated` (lines 167-171)
- **Termination:** Closes on terminal status (line 149)
- **Error Handling:** Sends error JSON and closes connection (lines 175-183)

**WebSocket /api/stream/projects/{project_id}/workflows/{run_id}** (Lines 191-236):
- **Purpose:** Stream workflow node events via WebSocket
- **Path Parameters:** `project_id: str`, `run_id: str`
- **Connection:** `connection_manager.connect(websocket, project_id)` (line 194)
- **Polling:** Polls node states every 1 second (line 210)
- **Node Events:** Sends all node states as `workflow.node_state.updated` (lines 212-216)
- **Run Events:** Sends `workflow.run.updated` on completion (lines 219-221)
- **Termination:** Closes on terminal status (line 220)
- **Note:** Currently uses agent service as proxy (line 199), workflow service not fully implemented

### Request/Response Models

All endpoints use Pydantic models for request/response validation:

**Common Models:**
- `PaginatedResponse[T]`: `{items: T[], next_cursor?: string | null, total?: number}`
- `MessageResponse`: `{message: string}`
- `ID`: String type alias

**Project Models:**
- `CortexProject`: Full project entity with id, name, slug, description, status, timestamps
- `CreateProjectRequest`: name (required), slug?, description?
- `UpdateProjectRequest`: All fields optional (name?, description?, status?, etc.)
- `DeleteProjectResponse`: `{success: bool}`

**Ingest Models:**
- `IngestJob`: Full job entity with id, project_id, source_path, status, stage, progress, timestamps
- `IngestRequest`: source_path (required), original_filename?, byte_size?, mime_type?, is_deep_scan?
- `IngestStatus`: Enum (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)
- `IngestStage`: Enum (UPLOAD, PARSING, CHUNKING, EMBEDDING, INDEXING, COMPLETE)

**Agent Models:**
- `AgentRun`: Full run entity with id, project_id, agent_id, status, input_prompt, timestamps
- `AgentRunRequest`: agent_id, project_id, input_prompt, context_item_ids?
- `AgentRunStatus`: Enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- `AgentStep`: Step entity with id, run_id, step_number, node_id, status, input_json, output_json, error, duration_ms
- `AgentMessage`: Message entity with id, run_id, role, content, context_item_ids_json, created_at
- `AgentNodeState`: Node state with run_id, node_id, status, progress, messages_json, timestamps
- `AppendMessageRequest`: content (required), role?, context_item_ids?
- `AgentProfile`: Agent metadata with id, name, description, system_prompt

**Workflow Models:**
- `WorkflowGraph`: Graph entity with id, project_id, name, description, graph_json, timestamps
- `WorkflowRun`: Run entity with id, project_id, workflow_id, status, input_json, output_json, checkpoint_json, timestamps
- `WorkflowRunStatus`: Enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED)
- `CreateWorkflowRunRequest`: workflow_id, input_data?
- `ExecuteWorkflowRunRequest`: input_data?
- `ResumeWorkflowRunRequest`: checkpoint_id?

**Roadmap Models:**
- `RoadmapNode`: Node entity with id, project_id, label, description, status, priority, dates, depends_on_ids_json, lane_id, idea_id, ticket_id
- `RoadmapEdge`: Edge entity with id, project_id, from_node_id, to_node_id, kind, label, created_at
- `RoadmapGraph`: Graph structure with nodes: List[RoadmapNode], edges: List[RoadmapEdge]
- `RoadmapNodeStatus`: Enum (PENDING, ACTIVE, COMPLETE, BLOCKED)
- `RoadmapPriority`: Enum (LOW, MEDIUM, HIGH)

**Knowledge Models:**
- `KnowledgeNode`: Node entity with id, project_id, title, content, type, embedding_json, metadata_json, timestamps
- `KnowledgeEdge`: Edge entity with id, project_id, source, target, type, weight, label, created_at
- `KnowledgeGraph`: Graph structure with nodes: List[KnowledgeNode], edges: List[KnowledgeEdge]
- `KnowledgeSearchRequest`: query (required), limit?, filters?

**Context Models:**
- `ContextItem`: Item entity with id, project_id, name, type, tokens, pinned, canonical_document_id, created_at
- `ContextBudget`: Budget entity with total_tokens, used_tokens, max_tokens, items: List[ContextItem]
- `AddContextItemsRequest`: items: List[ContextItem]
- `AddContextItemsResponse`: added_items: List[ContextItem], budget: ContextBudget
- `ContextItemType`: Enum (PDF, REPO, CHAT, OTHER)

**Ideas Models:**
- `IdeaCandidate`: Candidate entity with id, project_id, text, type, status, confidence, source_quotes, created_at
- `IdeaCluster`: Cluster entity with id, project_id, name, summary, idea_ids_json, timestamps
- `IdeaTicket`: Ticket entity with id, project_id, title, description, status, priority, origin_idea_ids_json, related_files_json, timestamps
- `MissionControlTask`: Task entity with id, project_id, title, description, column, origin, confidence, context, timestamps
- `IdeaTicketStatus`: Enum (BACKLOG, TODO, IN_PROGRESS, DONE, BLOCKED)
- `IdeaTicketPriority`: Enum (LOW, MEDIUM, HIGH)

**Gap Analysis Models:**
- `GapReport`: Report entity with id, project_id, generated_at, suggestions: List[GapSuggestion]
- `GapSuggestion`: Suggestion entity with id, report_id, project_id, ticket_id, status, notes, confidence, related_files_json

**Mode Models:**
- `ProjectExecutionSettings`: Settings entity with project_id, mode, llm_temperature, validation_passes, max_parallel_tools
- `ExecutionMode`: Enum (NORMAL, PARANOID)
- `ProjectExecutionSettingsUpdateRequest`: mode?, llm_temperature?, validation_passes?, max_parallel_tools?

**System Models:**
- `SystemStatus`: Status entity with gpu_metrics, cpu_metrics, memory_metrics, context_metrics, overall_status
- `GpuMetrics`: GPU metrics with available, utilization_percent, memory_used_gb, memory_total_gb
- `CpuMetrics`: CPU metrics with utilization_percent, cores
- `MemoryMetrics`: Memory metrics with used_gb, total_gb, utilization_percent
- `ContextMetrics`: Context metrics with active_runs, total_tokens
- `SystemStatusLevel`: Enum (NOMINAL, WARNING, CRITICAL)

### Authentication & Authorization

**Token Generation:**
- Endpoint: `POST /api/token`
- Flow: OAuth2 password flow (form data: username, password)
- Token Type: JWT Bearer token
- Expiry: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Secret: `settings.auth_secret` (default "a_very_secret_key", MUST be changed in production)

**Token Usage:**
- Header: `Authorization: Bearer <token>`
- Validation: `verify_token()` dependency checks JWT signature and expiry
- Skip Auth: If `settings.debug` or `settings.skip_auth` is True, auth is bypassed

**Protected Endpoints:**
- All endpoints except `/api/token` and `/api/system/health` require authentication
- Auth enforced via `auth_deps` list in `main.py` (line 45-49)
- Missing/invalid token returns 401 Unauthorized

**Project Scoping:**
- Most endpoints are project-scoped via `project_id` path parameter
- Services validate `project_id` matches resource ownership
- Returns 404 if resource doesn't belong to project

### Error Handling

**HTTP Status Codes:**
- `200 OK`: Successful GET/PATCH/DELETE
- `201 Created`: Successful POST (resource created)
- `202 Accepted`: Async operation accepted (workflow execute/resume)
- `204 No Content`: Successful DELETE (no response body)
- `400 Bad Request`: Validation error, invalid request body, business logic error
- `401 Unauthorized`: Missing/invalid authentication token
- `404 Not Found`: Resource not found or doesn't belong to project
- `409 Conflict`: Resource already exists (duplicate edge, etc.)
- `500 Internal Server Error`: Unexpected server error
- `501 Not Implemented`: Feature not implemented (chat segments repository)

**Error Response Format:**
- FastAPI default: `{"detail": "error message"}`
- Custom `HTTPException`: `HTTPException(status_code=400, detail="message")`
- Validation errors: Pydantic validation errors returned as JSON

**Common Error Scenarios:**
- Missing required fields: 400 with validation details
- Resource not found: 404 with "Resource not found" message
- Project ID mismatch: 404 with "Resource not found" (security: doesn't reveal existence)
- Invalid status transition: 400 with current status message
- Budget overflow: 400 with "Context budget exceeded" message
- Duplicate resource: 409 with "already exists" message

### Pagination

**Cursor-Based Pagination:**
- Query parameter: `cursor?: string` (base64-encoded offset or ID)
- Limit: `limit: int` (default 50, range 1-100)
- Response: `PaginatedResponse` with `items`, `next_cursor?`, `total?`
- Implementation: Fetches `limit + 1` rows to detect next page
- Next cursor: Set if more items available, `null` if last page

**Offset-Based Pagination (Legacy):**
- Some endpoints use integer offset from cursor string
- `ProjectRepository.list_projects()` uses offset-based pagination

### Streaming

**WebSocket Streaming:**
- Endpoints: `/api/stream/projects/{project_id}/ingest/{job_id}`, `/api/stream/projects/{project_id}/agent-runs/{run_id}`, `/api/stream/projects/{project_id}/workflows/{run_id}`
- Connection: `connection_manager.connect(websocket, project_id)`
- Events: JSON payloads with `type` and data fields
- Polling: 1-second polling interval (production should use event-driven)
- Disconnect: Clean disconnect handling, connection cleanup

**Server-Sent Events (SSE):**
- Endpoint: `/api/stream/projects/{project_id}/ingest/{job_id}/events`
- Format: `event: {type}\n` `data: {json}\n\n`
- Media Type: `text/event-stream`
- Polling: 1-second polling interval
- Termination: Closes on terminal status

**Event Types:**
- Ingest: `ingest.job.created`, `ingest.job.{status}` (queued, running, completed, failed, cancelled)
- Agent: `agent.run.created`, `agent.run.{status}`, `agent.step.updated`, `agent.message.appended`, `workflow.node_state.updated`
- Workflow: `workflow.node_state.updated`, `workflow.run.updated`
- Error: `{"error": "error_type", "message": "details"}`

---

## Documentation & Specifications Analysis

The documentation structure (`docs/`) provides comprehensive specifications for unfinished work, organized into three categories: Test Specifications, API Specifications, and Feature Specifications. All specifications follow consistent formats and reference existing code patterns.

### Documentation Structure (`docs/specs/`)

**Directory Organization:**
- `test-specs/`: Detailed test cases for unfinished features (backend/ and frontend/ subdirectories)
- `api-specs/`: API endpoint specifications and OpenAPI schemas
- `feature-specs/`: Implementation specifications for incomplete features (backend/, frontend/, integration/ subdirectories)
- `README.md`: Overview and usage guide for all specifications

**Specification Count:**
- Test Specs: 14 files (9 backend, 3 frontend, 2 service-level)
- API Specs: 7 endpoint specs + 2 OpenAPI schemas
- Feature Specs: 12 files (6 backend, 4 frontend, 3 integration)

### Test Specifications (`docs/specs/test-specs/`)

**Backend API Test Specs:**
- `test-spec-ingest-api.md`: DELETE endpoint, cancel operations, pagination, filtering
- `test-spec-roadmap-api.md`: Full CRUD operations, graph validation, node/edge management
- `test-spec-knowledge-api.md`: Graph operations, node/edge CRUD, search functionality
- `test-spec-context-api.md`: POST/PATCH endpoints, budget management, item operations
- `test-spec-agents-api.md`: Missing endpoints (get run, steps, messages, cancel)
- `test-spec-ideas-api.md`: Project-scoped routes, filtering, pagination
- `test-spec-workflows-api.md`: Workflow execution, node state management

**Service Test Specs:**
- `test-spec-idea-service.md`: Database persistence migration for IdeaService
- `test-spec-context-service.md`: Database persistence migration for ContextService
- `test-spec-workflow-service.md`: Database persistence migration for WorkflowService
- `test-spec-gap-analysis-repo.md`: Database migration for GapAnalysisRepo

**Frontend Test Specs:**
- `test-spec-ingest-station.md`: Delete mutation, error states, file upload
- `test-spec-mission-control.md`: Context derivation, drag-drop functionality
- `test-spec-hooks.md`: Missing React hooks and mutations

**Test Spec Format:**
- Test scenarios with setup, action, expected results
- Edge cases and error conditions
- Test data structures and fixtures
- Dependencies and setup requirements
- Integration with existing test patterns

### API Specifications (`docs/specs/api-specs/`)

**Endpoint Specs:**
- `api-spec-ingest-endpoints.md`: DELETE, cancel, get job endpoints
- `api-spec-roadmap-endpoints.md`: Full CRUD for nodes/edges, graph operations
- `api-spec-knowledge-endpoints.md`: Graph operations, node/edge CRUD, search
- `api-spec-context-endpoints.md`: POST/PATCH endpoints, budget management
- `api-spec-agents-endpoints.md`: Get run, steps, messages, cancel endpoints
- `api-spec-ideas-endpoints.md`: Project-scoped routes structure
- `api-spec-streaming-endpoints.md`: WebSocket/SSE event specifications

**OpenAPI Schemas:**
- `openapi-missing-endpoints.yaml`: Complete OpenAPI 3.0 spec for missing endpoints
- `openapi-error-responses.yaml`: Standardized error response schemas

**API Spec Format:**
- Endpoint definitions with HTTP method, path, parameters
- Request/response schemas with field types and constraints
- Error responses with status codes and messages
- Authentication requirements
- Examples and use cases
- Integration with existing `api-contract.md`

### Feature Specifications (`docs/specs/feature-specs/`)

**Backend Feature Specs:**
- `feature-spec-database-persistence.md`: Migration plan for in-memory services to database
- `feature-spec-project-scoped-routes.md`: Refactoring plan for project-scoped API structure
- `feature-spec-ingest-deletion.md`: Delete job endpoint specification
- `feature-spec-roadmap-crud.md`: Complete roadmap CRUD operations
- `feature-spec-agent-run-details.md`: Agent run details, steps, messages endpoints
- `feature-spec-context-management.md`: Context budget management, item operations

**Frontend Feature Specs:**
- `feature-spec-ingest-deletion-ui.md`: Delete mutation implementation in IngestStation
- `feature-spec-mission-control-context.md`: Context derivation from ticket data
- `feature-spec-missing-hooks.md`: React hooks for missing API endpoints
- `feature-spec-error-handling.md`: Comprehensive error handling across components

**Integration Feature Specs:**
- `feature-spec-qdrant-integration.md`: Vector database integration for knowledge graph
- `feature-spec-langgraph-integration.md`: LangGraph workflow execution integration
- `feature-spec-streaming-events.md`: Real-time event streaming implementation

**Feature Spec Format:**
- Current state analysis (what exists, what's missing)
- Target state definition (complete feature description)
- Technical design (architecture, data flow, algorithms)
- Implementation steps (detailed task breakdown)
- Testing strategy (unit, integration, E2E tests)
- Success criteria (acceptance tests, performance metrics)

### API Contract Document (`docs/api-contract.md`)

**Structure:**
- High-level, implementation-agnostic contract
- Domain entities referenced from `src/domain/types.ts`
- Conventions: Base URL `/api`, token auth, ISO-8601 dates, string IDs
- Pagination: Cursor-based with `PaginatedResponse<T>` envelope

**Sections:**
1. Projects: List, create, get, update, delete
2. Ingest & Sources: Sources CRUD, jobs CRUD, file upload
3. Canonical Documents, Chunks, Clusters: Document management
4. Agents: Profiles, runs, steps, messages, node states
5. Workflows: Graphs, runs, execution, pause/resume
6. Roadmap: Nodes, edges, graph operations
7. Knowledge Graph: Nodes, edges, search
8. Context: Budget, items CRUD
9. Ideas: Candidates, clusters, tickets, mission control tasks
10. Gap Analysis: Run analysis, get reports, history
11. Project Intel: Rebuild ideas, list candidates/clusters/tickets
12. Mode: Get/update execution settings
13. System: Health, status

**Status:**
- Some endpoints in contract not yet implemented (e.g., ingest sources CRUD)
- Some implemented endpoints differ from contract (e.g., ingest job creation)
- Contract serves as target state for API evolution

### Specification Usage Patterns

**For Developers:**
1. Review relevant test specs before implementing features
2. Follow API specs when implementing endpoints
3. Use feature specs as implementation guides
4. Reference OpenAPI schemas for API contracts

**For Testers:**
1. Use test specs to write comprehensive test suites
2. Follow test cases and edge cases specified
3. Verify implementations match specifications

**For Product/Project Managers:**
1. Review feature specs to understand scope
2. Use specs for planning and estimation
3. Track implementation progress against specs

### Key Reference Files

**Code References:**
- `../api-contract.md`: Existing API contract (source of truth)
- `backend/app/api/routes/*.py`: Current route implementations
- `backend/app/services/*.py`: Service implementations
- `frontend/components/*.tsx`: Frontend components with TODOs
- `frontend/src/hooks/*.ts`: Existing hooks
- `backend/tests/*.py`: Existing test patterns

### Specification Completeness

**Coverage:**
- All identified unfinished work documented
- Consistent formats across all specs
- References to existing code patterns
- Actionable test cases and implementation steps

**Status Tracking:**
- Specs document current state vs target state
- Implementation progress can be tracked against specs
- Test coverage can be verified against test specs

**Quality:**
- OpenAPI specs follow OpenAPI 3.0 standard
- Test specs provide actionable test cases
- Feature specs provide enough detail for implementation
- All specs reference existing codebase patterns

---

## Summary Statistics

**Backend:**
- 14 API route modules
- 18 service modules
- 5 repository modules
- 1 LangGraph graph definition
- 1 tool integration (n8n)
- 20+ database tables
- 50+ API endpoints
- 14 route modules with detailed endpoint breakdowns
- Comprehensive request/response model documentation

**Frontend:**
- 8 custom hooks
- 3 core components (ErrorBoundary, ErrorDisplay, ToastContainer)
- 1 state store (Zustand)
- 1 API client with 50+ functions
- Comprehensive TypeScript type definitions

**Testing:**
- 11 backend test modules
- 7 E2E test specs
- Test fixtures and utilities
- WebSocket test client

**Configuration:**
- Nix flakes and shell.nix
- Docker Compose for services
- Environment-based configuration
- Deployment scripts

**Documentation:**
- 14 test specification files (9 backend, 3 frontend, 2 service-level)
- 7 API endpoint specification files
- 2 OpenAPI schema files
- 12 feature specification files (6 backend, 4 frontend, 3 integration)
- 1 comprehensive API contract document

**API Coverage:**
- Authentication: 1 endpoint (token generation)
- Projects: 5 endpoints (CRUD operations)
- Ingest: 6 endpoints (jobs CRUD, upload, cancel, delete)
- Agents: 11 endpoints (profiles, runs, steps, messages, node states, streaming)
- Workflows: 9 endpoints (graphs, runs, execute, pause/resume, cancel, status)
- Roadmap: 9 endpoints (nodes CRUD, edges CRUD, graph)
- Knowledge: 8 endpoints (graph, nodes CRUD, edges CRUD, search)
- Context: 5 endpoints (budget, items CRUD, list)
- Ideas: 10 endpoints (candidates, clusters, tickets, tasks CRUD)
- Gap Analysis: 3 endpoints (run, latest, history)
- Project Intel: 5 endpoints (rebuild, list candidates/clusters/tickets, update ticket)
- Mode: 2 endpoints (get/update execution settings)
- System: 2 endpoints (health, status)
- Streaming: 4 endpoints (WebSocket ingest/agent/workflow, SSE ingest)

**Total:** 80+ documented endpoints across 14 route modules

This analysis covers the complete codebase structure, implementation patterns, data flows, integration points, API contract details, and documentation specifications for Project Cortex.


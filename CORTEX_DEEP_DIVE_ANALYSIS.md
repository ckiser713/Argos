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


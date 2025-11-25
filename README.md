# Cortex – AI-Integrated Knowledge & Execution Engine

Cortex is a single-user, power-user–oriented system that turns fragmented notes, chat logs, repos, and research into a coherent execution engine.

At a high level:

- **Frontend**: React + TypeScript cyberpunk dashboard (glassmorphism, neon, node/graph UIs).
- **Backend**: FastAPI + Python 3.11 with Pydantic-typed REST and streaming endpoints.
- **Orchestration**: LangGraph for deterministic agent flows; n8n for side-band automations.
- **Runtimes & Storage**: vLLM / llama.cpp / custom PyTorch (ROCm) for inference; Qdrant for vector search; PostgreSQL for metadata and state.

The guiding principles are:

- **Separation of concerns** – UI is purely presentational; data flows through small, typed hooks and API clients.
- **Determinism** – workflows are explicit graphs, not hidden chains of random tool calls.
- **Runtime decoupling** – models and tools live behind abstract services; the frontend never calls a model directly.
- **Observability** – logs, metrics, and structured errors are first-class.

## Architecture

### High-level data flow

```mermaid
graph TD
    A[React Frontend] -- HTTPS / WS --> B(FastAPI Backend);
    B -- service layer --> C{LangGraph Flows};
    C -- orchestrates --> D[vLLM / Open-weight LMs];
    C -- orchestrates --> E[llama.cpp / local models];
    C -- orchestrates --> F[Custom PyTorch (ROCm) tools];
    D -- uses --> G(Qdrant / PostgreSQL);
    E -- uses --> G;
    F -- uses --> G;
    G -- notifies --> H[n8n Workflows];

    subgraph Frontend
        A
    end

    subgraph Backend
        B
    end

    subgraph Orchestration
        C
    end

    subgraph Runtimes
        D
        E
        F
    end

    subgraph Storage
        G
    end

    subgraph External Integrations
        H
    end
```
**Explanation of the diagram:**

```
┌─────────────────────┐      HTTPS / WS       ┌──────────────────────────┐
│  React Frontend     │  typed `cortexApi`   │ FastAPI Backend          │
│  (TypeScript, RQ)   ├──────────────────────▶│ /api/* + /streams/*      │
└─────────────────────┘                      └──────────┬───────────────┘
                                                      │ service layer
                                                      │
                                                      ▼
                                            ┌──────────────────────┐
                                            │ LangGraph Flows      │
                                            │ (agents, tools)      │
                                            └─────────┬────────────┘
                                                      │
                              ┌───────────────────────┼────────────────────────┐
                              ▼                       ▼                        ▼
                     ┌────────────────┐     ┌────────────────┐       ┌────────────────┐
                     │ vLLM /         │     │ llama.cpp /    │       │ Custom PyTorch │
                     │ Open-weight LMs│     │ local models   │       │ (ROCm) tools   │
                     └────────────────┘     └────────────────┘       └────────────────┘
                              ▼                       ▼                        
                       ┌───────────────────────────────────────────────────────┐
                       │ Qdrant (vectors) + PostgreSQL (metadata, jobs, DAGs) │
                       └───────────────────────────────────────────────────────┘

                              ▼
                     ┌────────────────┐
                     │ n8n Workflows  │  (webhooks, syncs, notifications)
                     └────────────────┘
```

### Layer responsibilities

-   **React frontend**
    -   Implements the cyberpunk dashboard: Ingest Station, Mission Control, Knowledge Nexus, Deep Research, Strategy Deck, Repo Analysis, etc.
    -   Talks to the backend exclusively via typed API client (`src/lib/cortexApi.ts`) and data hooks (React Query + Zustand for identity/state).
    -   Renders workflow graphs, ingest tables, agent timelines, and context budgets but has no knowledge of models, embeddings, or vector stores.

-   **FastAPI backend**
    -   Owns the public API contract (`/api/projects`, `/api/ingest/jobs`, `/api/roadmap`, `/api/agents/runs`, `/api/knowledge/graph`, `/api/context`, etc.).
    -   Uses Pydantic models that mirror the frontend domain types (`CortexProject`, `IngestJob`, `AgentRun`, `KnowledgeNode`, `RoadmapNode`, …).
    -   Delegates work to internal services (`IngestService`, `RagService`, `RoadmapService`, `AgentService`, `RepoService`).
    -   Exposes streaming endpoints (SSE/WebSocket) for long-running jobs (ingest, agent runs, repo analysis).

-   **LangGraph orchestration**
    -   Encodes agent flows as explicit graphs: nodes are tools or sub-agents, edges define transitions.
    -   Provides deterministic execution, state snapshots, and event streams that feed the frontend’s Agent Visualization.
    -   Wraps tooling around models, vector search, and external systems (Git, GitHub, issue trackers, web fetchers).

-   **Model runtimes (vLLM, llama.cpp, PyTorch)**
    -   Exposed via internal interfaces like `LanguageModelRunner`, `EmbeddingRunner`, `CodeModelRunner`.
    -   The FastAPI layer talks to these through services only; no external caller ever sees raw model configs.

-   **Qdrant + PostgreSQL**
    -   Qdrant stores vectorized chunks, code segments, and knowledge nodes.
    -   PostgreSQL stores projects, ingest jobs, agent runs, roadmap DAGs, and metadata required to reconstruct state.

-   **n8n**
    -   Handles side-effectful, “workflow-y” tasks that don’t belong in LangGraph: backup syncs, notifications, scheduled health checks, integrations with external SaaS.

## Features

### 1. Ingestion & Doc Atlas

-   Drag-and-drop files, paste URLs, or ingest chat exports and repos.
-   **Ingestion pipeline:**
    -   Source registration (`IngestSource`).
    -   Pre-processing (OCR, HTML/Markdown normalization).
    -   Canonicalization (`CanonicalDocument`) – de-duplicate and normalize content.
    -   Chunking & embedding into Qdrant (`Chunk`, `Cluster`).
    -   Linking to projects and roadmap nodes.
-   **Frontend Ingest Station shows:**
    -   Job table with stage, status, source type, progress bars, and timestamps.
    -   Per-job drill-down into errors, canonical docs, and resulting chunks.

### 2. RAG + Knowledge Nexus

-   **RAG engine built on LangGraph tools:**
    -   Query rewriting / decomposition.
    -   Vector search over Qdrant, constrained by project, tag, or roadmap node.
    -   Response synthesis using vLLM/llama.cpp.
-   **Knowledge Nexus visualizes the knowledge graph:**
    -   Nodes: documents, concepts, clusters, code symbols.
    -   Edges: citations, derivations, “inspired-by”, and semantic relationships.
    -   Node sizing based on weight/importance; coloring by type or project.

### 3. Dynamic Roadmap DAG

-   Each project has a roadmap DAG (`RoadmapNode`, `RoadmapEdge`):
    -   Nodes represent milestones, workstreams, or automation stages.
    -   Edges capture dependencies (e.g., “Ingest → Canonicalize → Repo Audit → Architecture Draft”).
-   **WorkflowVisualizer renders the DAG:**
    -   Status-aware nodes (Pending, Active, Complete, Blocked).
    -   Live overlay from LangGraph events to show which nodes/edges are currently active.

### 4. Agent Visualization & Mission Control

-   LangGraph-based agents for research, planning, and refactoring.
-   Agent runs (`AgentRun`, `AgentStep`, `AgentNodeState`) are surfaced in Mission Control:
    -   Timeline of steps with reasoning snippets and tool calls.
    -   Node-level heat map for which parts of the graph did the work.
    -   Streaming updates during long runs; final summary appended to project context.

### 5. Repo Analysis & Code-Aware RAG

-   Ingest Git repositories (local or remote) as a source type:
    -   Parse modules, functions, and tests into `CanonicalDocument` + code-specific metadata.
    -   Embed symbols, call graphs, and tests for code-aware RAG.
-   **Repo panels in the UI:**
    -   High-level architecture view (packages, services).
    -   Hotspots, coverage gaps, and suggested refactors produced by LangGraph flows.

## Decoupling & Type Safety

Cortex is designed to keep responsibilities clean and swappable.

-   **Frontend decoupling**
    -   All network calls go through `src/lib/http.ts` and `src/lib/cortexApi.ts`.
    -   UI components use hooks like `useIngestJobs`, `useRoadmap`, `useKnowledgeGraph`, `useAgentRuns`, `useContextItems`.
    -   Domain types live in `src/domain/types.ts`, aligned with backend Pydantic models.

-   **Backend decoupling**
    -   Pydantic models in `app/domain/models.py` define the canonical API surface.
    -   Service layer (e.g., `app/services/ingest_service.py`, `app/services/rag_service.py`) abstracts runtime details.
    -   Model backends implement small interfaces; you can swap vLLM ↔ llama.cpp ↔ remote APIs without touching routes.

-   **No direct model calls from the UI**
    -   There are no endpoints like `/v1/completions` exposed to the browser.
    -   All operations are task-oriented: “start agent run”, “generate roadmap”, “suggest refactors”, “answer question with RAG”.

## Getting Started

### Repository layout

A typical checkout of Cortex looks like:

```
cortex/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Settings (env-based)
│   │   ├── domain/           # Pydantic models
│   │   ├── api/              # Routers grouped by resource
│   │   └── services/         # Ingest, RAG, agents, repo, roadmap, context
│   └── tests/                # pytest tests (API + services)
├── frontend/
│   ├── src/
│   │   ├── components/       # UI components (IngestStation, WorkflowVisualizer, …)
│   │   ├── hooks/            # useIngestJobs, useRoadmap, useKnowledgeGraph, …
│   │   ├── lib/              # http, cortexApi
│   │   └── domain/           # shared TS domain types
│   └── vite.config.ts        # Vite dev server
├── orchestration/
│   ├── langgraph/            # LangGraph flows & runners
│   └── n8n/                  # n8n workflow definitions
└── ops/
    ├── docker-compose.yml    # Qdrant, Postgres, n8n, observability stack
    └── env.example           # Example environment variables
```

### Prerequisites

-   Python 3.11+
-   Node.js 20+ and pnpm/yarn/npm
-   Docker (for Qdrant, Postgres, n8n, and optional observability stack)

### Development Environment Setup

1.  Install [Docker](https://docs.docker.com/get-docker/).
2.  Install [Docker Compose](https://docs.docker.com/compose/install/) (V2 is recommended).
3.  Install Python 3.11+.
4.  Install Node.js 18+.
5.  Run `ops/check_env.sh` to verify your environment.

### Development

#### 1. Backend (FastAPI) – dev mode

From the project root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install "fastapi[standard]" uvicorn pydantic pydantic-settings # Assuming only these for the skeleton
# For a full project, you'd have: pip install -r requirements.txt
```

Configure environment variables (or use `backend/.env`):

```bash
export CORTEX_ENV=dev
export CORTEX_DB_URL="postgresql+psycopg://cortex:cortex@localhost:5432/cortex"
export CORTEX_QDRANT_URL="http://localhost:6333"
export CORTEX_LOG_LEVEL=INFO
```

Run the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:

-   Interactive docs (Swagger): `http://localhost:8000/api/docs`

#### 2. Frontend (React + Vite) – dev mode

From the project root:

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend will be available at `http://localhost:5173`

### Testing

#### Backend Tests

```bash
cd backend
pytest
```

#### E2E Tests

E2E tests use Playwright and test the full stack (frontend + backend).

1. Install dependencies:
```bash
pnpm install
pnpm exec playwright install --with-deps
```

2. Run tests:
```bash
pnpm e2e
```

For more details, see [e2e/README.md](e2e/README.md)
-   ReDoc: `http://localhost:8000/api/redoc`

#### 2. Frontend (React) – dev mode

From the project root:

```bash
cd frontend
# If using pnpm workspaces (recommended for monorepo):
# pnpm install
# pnpm dev
# Otherwise, for a standalone frontend:
npm install # or yarn install
npm run dev # or yarn dev
```

The frontend will typically be available at `http://localhost:5173`.

#### 3. Running LangGraph Flows (local)

LangGraph flows are defined in `orchestration/langgraph/`. These are Python modules that can be executed directly or through a runner.

Example (assuming a `run.py` script exists in `orchestration/langgraph/runners/`):

```bash
cd orchestration/langgraph
python runners/local_runner.py --graph ingestion_graph --input "path/to/my/docs"
```

#### 4. Running n8n Workflows (local)

n8n workflows are defined as JSON files in `orchestration/n8n/workflows/`. You can import these into a running n8n instance.

To run n8n locally via Docker:

```bash
cd ops
docker-compose up -d n8n
```

Access the n8n UI at `http://localhost:5678` (default port) and import workflows.

## Observability

Cortex emphasizes built-in observability:

-   **Structured Logging**: All backend services emit structured JSON logs (e.g., using `loguru` or `structlog`) to stdout, making them easy to consume by tools like Loki or ELK stack.
-   **Metrics**: Integration with Prometheus for key metrics (API latency, job queue sizes, agent step durations).
-   **Tracing**: OpenTelemetry (or similar) stubs are in place for distributed tracing across services and LangGraph steps.
-   **Error Handling**: Explicit `ApiError` types on the frontend and `HTTPException` mapping on the backend ensure consistent error reporting.

## Future Roadmap

1.  **Phase 1: Core Functionality (Current Focus)**
    -   Complete all backend API endpoints and streaming.
    -   Integrate frontend with all data hooks.
    -   Basic LangGraph flows for ingestion and RAG.
    -   Initial Qdrant integration.

2.  **Phase 2: Advanced Orchestration & Model Integration**
    -   Full LangGraph implementation for complex agentic workflows (planning, code generation, self-correction).
    -   Robust vLLM/llama.cpp/PyTorch adapter implementation with ROCm optimization.
    -   Deep integration with n8n for automation and external services.

3.  **Phase 3: Collaboration & Scalability (Long-term)**
    -   Multi-user support and access control.
    -   Distributed LangGraph execution.
    -   Cloud deployment strategies.
    -   Enhanced UI for administration and monitoring.

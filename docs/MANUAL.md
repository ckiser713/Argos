# Argos Technical Manual

Argos is an AI-integrated knowledge and execution engine built for speed, determinism, and deep insight. This manual serves as the single source of truth for architecture, deployment, and development.

## 🏗 Architecture

Argos is structured as a native Linux application optimized for Nix-based environments.

### 1. Presentation (Frontend)
- **Tech Stack**: React, TypeScript, Vite.
- **Role**: Cyberpunk-inspired dashboard for ingestion, mission control, and knowledge visualization.

### 2. Logic (Backend)
- **Tech Stack**: FastAPI, Python 3.11, Pydantic, SQLAlchemy.
- **Role**: REST/Streaming API, business logic, and service orchestration.

### 3. Orchestration (Agents)
- **Tech Stack**: LangGraph.
- **Role**: Deterministic agentic workflows that manage tool execution and state transitions.

### 4. Data & Runtime
- **Database**: PostgreSQL (State/Metadata), SQLite (Local Dev).
- **Vector Store**: Qdrant.
- **Inference**: vLLM and llama.cpp (ROCm optimized).

---

## ❄️ Nix Environment

Argos uses Nix for fully reproducible development and deployment.

### Entering the Dev Environment
```bash
nix develop
```
This shell provides:
- Python 3.11 with Poetry
- Node.js 20 with pnpm
- Qdrant & PostgreSQL (if configured as services)

---

## 🖥 Deployment (Systemd)

Argos is deployed as a suite of systemd services on native Linux.

### Configuration
Environment variables are managed in `/etc/argos/argos.env`. 
Key variables:
- `ARGOS_ENV`: `production`, `strix`, or `local`.
- `ARGOS_DATABASE_URL`: Connection string for PostgreSQL.
- `ARGOS_AUTH_SECRET`: JWT signing key.

### Services
- `argos-backend.service`: Primary API.
- `argos-frontend.service`: Static file serving or dev server.
- `argos-worker.service`: Ingestion and long-running agent tasks.

---

## 🛠 Development Workflow

### Adding a Model Lane
1. Define the lane in `backend/app/config.py`.
2. Update the routing logic in `backend/app/services/llm_service.py`.
3. Test using `nix develop --command pytest`.

### Ingestion Pipeline
Ingest flows are defined in `backend/app/services/ingest_service.py`. All documents are canonicalized before embedding.

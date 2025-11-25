# Cortex Backend Skeleton (FastAPI)

This is a minimal FastAPI backend skeleton for **Project Cortex**.  
It exposes typed HTTP APIs for core domains (system, context, workflows, ingest, agents, ideas, knowledge) using
Pydantic models and in-memory stub implementations.

## 1. Requirements

- Python **3.11+**
- Recommended: virtual environment (e.g. `venv` or `uv`)

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install "fastapi[standard]" uvicorn pydantic pydantic-settings
```
If you later add database, model runtimes, or other infra, extend pip deps here.

## 2. Run the server
From the project root (where the `app/` package lives):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at:

- Interactive docs (Swagger): http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 3. High-level structure
- `app/config.py` – application settings via `pydantic-settings`.
- `app/domain/models.py` – Pydantic domain models (context, workflows, ingest, agents, ideas, knowledge, system).
- `app/services/*.py` – in-memory service layers; later you can swap these for DB/model-backed implementations.
- `app/api/routes/*.py` – FastAPI routers grouped by resource.
- `app/main.py` – FastAPI app factory and router wiring.

## 4. Next steps
- Align these models and routes with `docs/api-contract.md` and `src/domain/types.ts` once those are finalized.
- Replace in-memory services with real persistence (PostgreSQL, etc.).
- Connect runtime orchestration (LangGraph / n8n / PyTorch / vLLM / llama.cpp) behind the existing service interfaces.

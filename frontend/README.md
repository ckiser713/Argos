<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Cortex Frontend (Vite + React)

Thin UI shell for the Cortex backend (`/api/*` + `/api/stream/*`). No AI Studio/Gemini dependencies remain.

## Prerequisites
- Node 20+
- pnpm (preferred) or npm

## Run locally
```bash
pnpm install
# Point the UI at your backend (default: http://localhost:8000)
echo 'VITE_CORTEX_API_BASE_URL=http://localhost:8000' > .env.local
pnpm dev
```

### Backend & auth expectations
- Backend API: FastAPI at `/api`. Local dev usually runs with `CORTEX_SKIP_AUTH=1`; otherwise obtain a token via `POST /api/auth/token` and store the `access_token` in `localStorage.cortex_auth_token` (the HTTP client reads it automatically).
- Demo user (non-prod) can be created via `poetry run python scripts/seed_demo.py --with-demo-user` → username `demo`, password `demo1234`.

### First Run / Demo path (minimal models)
1) Download minimal models: `bash ops/download_minimal_models.sh`  
2) Start Qdrant: `docker-compose -f ops/docker-compose.yml up -d qdrant`  
3) Start a tiny LLM endpoint (vLLM or `llama-server`) and export:
   - `CORTEX_LLM_BACKEND=local_http`
   - `CORTEX_LLM_BASE_URL=http://localhost:8000/v1` (or your llama-server port)
   - `CORTEX_LLM_MODEL=TinyLlama-1.1B-Chat-v1.0`
   - `CORTEX_SKIP_AUTH=1` (for local)
4) Start backend: `cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000`
5) Seed demo data: `cd backend && poetry run python scripts/seed_demo.py --with-demo-user --smoke-query "summarize the demo workspace"`
6) Start frontend: `cd frontend && VITE_CORTEX_API_BASE_URL=http://localhost:8000 pnpm dev`

See `docs/DEMO_MODE.md` for a fuller smoke-test walkthrough (ingest → embed → query).

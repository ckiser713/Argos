# Demo Mode & Minimal-Model Smoke Test

This guide brings the stack up with tiny models so you can verify ingest → embed → query end-to-end after a deploy.

## Prerequisites
- Python 3.11 with Poetry (backend)
- Node 20 with pnpm (frontend)
- Docker running (for Qdrant)
- Optional: vLLM installed locally; otherwise use `llama.cpp`'s `llama-server`.

## 1) Download the minimal models
```bash
bash ops/download_minimal_models.sh
# Uses TinyLlama (vLLM + GGUF) and stores them under ./models/minimal
```

## 2) Start dependencies
```bash
# Qdrant only (enough for demo)
docker-compose -f ops/docker-compose.yml up -d qdrant

# Minimal LLM endpoint (Option A: vLLM, preferred)
MODEL_DIR=./models/minimal/vllm/TinyLlama-1.1B-Chat-v1.0
python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_DIR" \
  --host 0.0.0.0 \
  --port 8000

# Minimal LLM endpoint (Option B: llama.cpp server, GGUF)
llama-server \
  --model ./models/minimal/gguf/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 11434 \
  --ctx-size 2048 \
  --api-server
```

Recommended backend env for the demo:
```bash
export ARGOS_SKIP_AUTH=1
export ARGOS_LLM_BACKEND=local_http
export ARGOS_LLM_BASE_URL=http://localhost:8000/v1   # or http://localhost:11434/v1 if using llama-server
export ARGOS_LLM_MODEL=TinyLlama-1.1B-Chat-v1.0
```

## 3) Start the backend
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 4) Seed the demo workspace and run a smoke query
```bash
cd backend
poetry run python scripts/seed_demo.py --with-demo-user --smoke-query "summarize the demo workspace"
# Creates project "Cortex Demo", ingests three fixture docs, and runs a RAG query.
# Demo user (non-production): demo / demo1234
```

## 5) Frontend
```bash
cd frontend
pnpm install
VITE_ARGOS_API_BASE_URL=http://localhost:8000 pnpm dev
```

## What to expect
- Three ingest jobs complete against the tiny fixtures.
- Smoke query returns at least one citation mentioning "ingest pipeline" or "roadmap".
- Frontend loads with live data; if auth is enabled, obtain a token via `/api/auth/token` and store it in `localStorage.cortex_auth_token`.


# Deployment Hardening Plan (Nix + ROCm, strix/production)

Authoritative checklist to lock down deployment across backend, inference lanes, data stores, and frontend. References: `nix/services.nix`, `nix/vllm.nix`, `nix/rocm.nix`, `backend/app/config.py`, `ops/docker-compose.yml`, `frontend/App.tsx`, `frontend/src/lib/http.ts`.

## 1) Lock deployment target & secrets (Nix + ROCm)
- Set `CORTEX_ENV=strix` (or `production`) in `nix/services.nix` env block; run services inside `nix develop` (backend already enforces `IN_NIX_SHELL`).
- Required env/secrets (keep in `/etc/cortex/cortex.env` and reference via `EnvironmentFile=` in systemd):
  - `CORTEX_AUTH_SECRET` (required in strix/prod), `CORTEX_SKIP_AUTH=false`.
  - `CORTEX_ALLOWED_ORIGINS=https://your-frontend.example` (comma-separated).
  - `CORTEX_DATABASE_URL=postgresql://USER:PASS@HOST:5432/cortex`.
  - `CORTEX_QDRANT_URL=http://qdrant:6333`.
  - `CORTEX_N8N_BASE_URL`, `CORTEX_N8N_API_KEY`.
  - `CORTEX_LLM_BACKEND=local_http`, `CORTEX_LLM_DEFAULT_LANE=orchestrator`.
  - Lane envs (one per lane): `CORTEX_LANE_ORCHESTRATOR_URL/MODEL/MODEL_PATH/BACKEND`, `CORTEX_LANE_CODER_*`, `CORTEX_LANE_FAST_RAG_*`, `CORTEX_LANE_SUPER_READER_*` (llama.cpp), `CORTEX_LANE_GOVERNANCE_*` (llama.cpp).
  - HIP/vLLM: `HIP_VISIBLE_DEVICES`, `HSA_OVERRIDE_GFX_VERSION=11.0.0`, `VLLM_TARGET_DEVICE=rocm`, `VLLM_ROCM_USE_AITER=1`, `VLLM_ROCM_USE_SKINNY_GEMM=1`, `GPU_MEM_UTIL` (0.45–0.60).
- Host mounts (systemd or Compose):
  - Models cache: `/mnt/models:/models` (share between vLLM + llama.cpp).
  - Qdrant data: `/var/lib/cortex/qdrant:/qdrant/storage`.
  - Logs: `StateDirectory=/var/lib/cortex` + `LOG_DIR=/var/log/cortex` (or bind `/var/log/cortex:/var/log/cortex`).

## 2) Model/runtime artifacts (ROCm GPU)
- vLLM ROCm container: build via Nix only — `nix build .#vllm-container` (image tag `vllm-rocm-nix:latest`, load with `docker load < result`). No prebuilt tarball/loader required.
- llama.cpp GGUF (ROCm-capable) for non-vLLM lanes: stage to `/models` and set:
  - `CORTEX_LANE_SUPER_READER_MODEL_PATH=/models/super_reader/<model>.gguf`
  - `CORTEX_LANE_GOVERNANCE_MODEL_PATH=/models/governance/<model>.gguf`
- vLLM lanes (orchestrator/coder/fast_rag): set `MODEL_PATH` for each lane and, if using container, pass via env or `EXTRA_VLLM_ARGS`.
- Pre-download embeddings to avoid cold starts (HF cache): `sentence-transformers/all-MiniLM-L6-v2`, `BAAI/bge-large-en-v1.5`, `nomic-ai/nomic-embed-text`. Prime cache with `HF_HOME=/models/hf_cache`.

## 3) Data stores & migrations
- Postgres: ensure DSN above; backend auto-switches in strix/prod. Run migrations before first boot:
  - `cd backend && poetry run python - <<'PY'\nfrom app.db import init_db; init_db()\nPY`
- Qdrant: enable in `ops/docker-compose.yml` (persistent volume already `./qdrant_storage:/qdrant/storage`); expose 6333/6334. Health: `curl http://qdrant:6333/healthz`.
- n8n: keep volume `./n8n_data:/home/node/.n8n`; set `N8N_BASIC_AUTH_*` or `N8N_API_KEY` + `CORTEX_N8N_BASE_URL` for backend calls.

## 4) Backend readiness & health
- Auth on: `CORTEX_SKIP_AUTH=false`, `CORTEX_AUTH_SECRET` non-empty; keep `/api/docs` behind auth by default.
- CORS: tighten `CORTEX_ALLOWED_ORIGINS` to deployed frontend only.
- Warmup/health: lane endpoints must answer `/v1/models` + `/health` for `model_warmup_service`; ensure vLLM/llama.cpp expose those and are reachable via lane URLs.
- RAG/ingest: set `CORTEX_QDRANT_URL` to service name; alerting—propagate ingest/Qdrant errors (FastAPI already returns error payloads; monitor logs from `app.services.ingest_service`).

## 5) Frontend: live data wiring
- API base: set `VITE_CORTEX_API_BASE_URL=https://backend.example` (consumed by `frontend/src/lib/http.ts`).
- Auth: populate `cortex_auth_token` in `localStorage` or wire a token provider to `setAuthTokenProvider`.
- Replace placeholders in `frontend/App.tsx`:
  - `KnowledgeNexus`: render data from `useKnowledgeGraph` (project-scoped) instead of “Coming Soon”.
  - `WorkflowConstruct`: use backend roadmap/workflow graph (hooks under `src/hooks`) and remove simulated sequence.
  - Mission control stats: bind to `useSystemStatus`/`useModelLanesStatus` and remove hardcoded metrics.
- Loading/error states: reuse existing query flags; drop mock context/workflow data.

## 6) Smoke tests & CI gates
- Backend (with Postgres + Qdrant + n8n running): `cd backend && poetry run pytest`.
- Frontend: `cd frontend && pnpm install --frozen-lockfile && pnpm test`.
- Playwright: `pnpm exec playwright test --project chromium` with `PLAYWRIGHT_BASE_URL=https://frontend.example` (backend reachable).
- Health curls (fail pipeline on non-200):
  - `curl -f http://inference-vllm:8000/health`
  - `curl -f http://llama-super-reader:8080/health`
  - `curl -f http://localhost:8000/api/docs` (FastAPI)
  - `curl -f http://qdrant:6333/healthz`

## 7) Deploy recipe (Nix)
- Build artifacts: `nix build .#vllm-container` (if containerizing), `nix build .#vllm-tools` for binaries.
- Bring-up (single host):
  - `nix develop` (ensures ROCm + Python env)
  - systemd units: `cortex-backend`, `cortex-frontend` (Vite preview), `cortex-docker` (Qdrant) with `EnvironmentFile=/etc/cortex/cortex.env` and mounts for models/qdrant/logs.
  - Inference lanes: either Nix systemd (`vllmSystemdService`) or Compose `inference-engine` with `/dev/kfd,/dev/dri`.
- Rollout steps: (1) Apply Nix config (units + env files + mounts) (2) Load/verify ROCm image + model paths (3) Run health curls (above) (4) Run backend pytest + frontend pnpm test (5) Run Playwright against live stack.
- Runbooks:
  - Model reload: adjust `MODEL_PATH`/lane env, `systemctl reload vllm` or `docker compose restart inference-engine`.
  - Lane switching: update `CORTEX_LLM_DEFAULT_LANE` + lane URLs; warmup check; restart backend.
  - Logs/metrics: `journalctl -u cortex-backend -f`, `journalctl -u vllm -f`, vLLM metrics via `curl /metrics` if enabled, ROCm `rocm-smi --showuse`.

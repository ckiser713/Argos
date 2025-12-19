# Deployment Guide - Nix Environment

## Prerequisites

Run the setup script to fix Nix permissions:

```bash
./setup-nix.sh
```

Then apply group changes:
```bash
newgrp nixbld
# OR log out and log back in
```

## Step 1: Enter Nix Development Shell

```bash
cd /home/nexus/Argos_Chatgpt
nix develop
```

This will provide:
- Python 3.11 with Poetry
- Node.js 20 with pnpm
- Playwright with browser dependencies
- Docker and docker-compose
- All required system libraries

## Step 2: Install Dependencies

### Backend (Python)
```bash
cd backend
poetry install
```

### Frontend (Node.js)
```bash
cd frontend
pnpm install
```

### Root (E2E Tests)
```bash
cd /home/nexus/Argos_Chatgpt
pnpm install
pnpm exec playwright install --with-deps
```

## Step 3: Start Docker Services (prod compose)

Prepare env: copy `ops/cortex.env.example` to `ops/.env` and fill **required** values:
- `CORTEX_AUTH_SECRET`, `POSTGRES_PASSWORD`, `CORTEX_DOMAIN`, `CORTEX_ADMIN_EMAIL`
- `MODELS_PATH`, `CORTEX_VLLM_IMAGE`, `LLAMA_CPP_IMAGE`, `HF_TOKEN` (if private models)
- `N8N_BASIC_AUTH_USER/PASSWORD`, `N8N_ENCRYPTION_KEY`

Build and run:
```bash
# Build backend + frontend builder (injects API base via build args)
docker compose -f ops/docker-compose.prod.yml build frontend-builder backend

# Run migrations first (gates app startup)
docker compose -f ops/docker-compose.prod.yml run --rm migrations

# Bring up core services (backend waits on migrations)
docker compose -f ops/docker-compose.prod.yml up -d backend caddy redis postgres qdrant
```

Models are not pulled automatically. Run `ops/download_minimal_models.sh` for smoke models or `ops/download_all_models.sh` for full lanes before first start. Set `HF_TOKEN` when required.

## Step 4: Run the Application (local dev alt)

### Terminal 1: Backend
```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd frontend
pnpm dev
```

### Terminal 3: E2E Tests (optional)
```bash
cd /home/nexus/Argos_Chatgpt
pnpm e2e
```

## Environment Variables

The Nix shell automatically sets:
- `CORTEX_ENV=local`
- `CORTEX_QDRANT_URL=http://localhost:6333`
- `CORTEX_DATABASE_URL=postgresql://cortex:cortex@localhost:5432/cortex`
- `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright`

For staging/production, set `CORTEX_DATABASE_URL` to your Postgres instance and run inside the Nix shell, or set `RUNNING_IN_DOCKER=1` (containers) / `CORTEX_ALLOW_NON_NIX=1` (systemd) to relax the guard. SQLite is only supported for `CORTEX_ENV=local`.

## Embeddings & Qdrant

- Defaults: `CORTEX_EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2`, `CORTEX_CODE_EMBEDDING_MODEL_NAME=jinaai/jina-embeddings-v2-base-code`.
- Device selection: set `CORTEX_EMBEDDING_DEVICE=cpu|cuda|rocm|auto` (backend image bakes PyTorch CPU wheels). For ROCm, override the wheel index and keep `CORTEX_EMBEDDING_DEVICE=rocm`.
- Require embeddings in prod: `CORTEX_REQUIRE_EMBEDDINGS=true` (auto-enabled when `CORTEX_ENV` is `strix`/`production`). Startup fails fast if embeddings or Qdrant are unreachable.
- Health: `/api/system/ready` gates on embeddings when required; `/api/system/embeddings/health` returns embedding/Qdrant readiness, device, and model names.
- Resource profile: all-MiniLM-L6-v2 uses ~500MB RAM and 1–2 CPU threads; the code model adds ~1.2GB. Ensure Qdrant is reachable at `CORTEX_QDRANT_URL` (defaults to `http://qdrant:6333` inside Docker).

## Quick Commands Reference

```bash
# Enter Nix shell
nix develop

# Build backend
nix build .#backend

# Build frontend
nix build .#frontend

# Build both
nix build

# Start Docker services
cortex-docker up -d

# Stop Docker services
cortex-docker down

# View Docker logs
cortex-docker logs -f
```

## Security & Containers

- Secrets: `ops/cortex.env.example` only contains placeholders. Keep prod secrets in Vault/SSM/SealedSecrets or an untracked env file and source them for Compose/systemd. Do not commit filled secrets or log API keys.
- n8n exposure: the UI is blocked by default; reach it only via VPN/IP allowlist/auth proxy. Set `N8N_ALLOWED_IPS`, `N8N_BASIC_AUTH_USER/PASSWORD`, and `N8N_ENCRYPTION_KEY` before enabling. Webhooks stay exposed only through Caddy.
- API limits: Caddy now rate-limits `/api/*` and `/webhooks/*` using `CORTEX_RATE_LIMIT_*` and `CORTEX_WEBHOOK_RATE_*` (overridable via env).
- Containers: backend image is multi-stage, pinned to `python:3.11.10-slim-bookworm`, and runs as non-root `cortex`. Compose pins third-party images and requires explicit, pinned tags for inference images.
- Defaults: n8n ports are no longer published directly; keep it behind the proxy and avoid host binds unless on a trusted network.

## Observability & Alerts
- Optional Prometheus service is defined in `ops/docker-compose.prod.yml` (config at `ops/prometheus.yml`). Start with `docker compose -f ops/docker-compose.prod.yml up -d prometheus`.
- Scrape targets include backend `/metrics`, vLLM, and llama.cpp. Add your own remote write/alertmanager if running a central stack.
- Suggested alerts: backend HTTP 5xx rate, ingest failures (`cortex_ingest_jobs_total{status="failed"}`), model lane health probes, and Redis queue depth (via INFO or custom exporter).

## Runbooks (Backups & Rotation)
- Postgres backup: `docker exec cortex-postgres pg_dump -U cortex cortex > backup.sql`; restore with `psql -U cortex -d cortex < backup.sql` (ensure app is stopped or in maintenance).
- Qdrant snapshot: `docker exec cortex-qdrant qdrant snapshot create --wait --snapshot-name cortex-$(date +%F).snap`; restore by stopping Qdrant and placing the snapshot in `/qdrant/snapshots`, then start with `--force-snapshot`.
- Auth secret rotation: set new `CORTEX_AUTH_SECRET`, deploy, then revoke all tokens via `scripts/bootstrap_admin.py --rotate-tokens` (or restart app to enforce new secret + blacklist old tokens).
- n8n credentials: rotate `N8N_BASIC_AUTH_USER/PASSWORD` and `N8N_ENCRYPTION_KEY`, restart n8n container, and re-run any credential tests.

## Troubleshooting

### Nix daemon permission denied
Run: `./setup-nix.sh` then `newgrp nixbld`

### Flakes not enabled
Check: `cat ~/.config/nix/nix.conf` should contain `experimental-features = nix-command flakes`

### Playwright browsers not installing
Run: `pnpm exec playwright install --with-deps` inside the Nix shell

### Docker socket permission denied
Add user to docker group: `sudo usermod -aG docker $USER` then log out/in

## Post-deploy smoke checklist (prod compose)
- `docker compose -f ops/docker-compose.prod.yml ps` shows backend healthy after migrations.
- `curl -f https://$CORTEX_DOMAIN/api/system/health` returns 200.
- Caddy serves frontend: `curl -I https://$CORTEX_DOMAIN`.
- Optional: run a quick Playwright smoke against `https://$CORTEX_DOMAIN` (`pnpm e2e:quick` from repo with `PLAYWRIGHT_BASE_URL` set).

















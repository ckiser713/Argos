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

## Step 3: Start Docker Services

```bash
# From project root, use the wrapper script
cortex-docker up -d

# Or use docker-compose directly
docker-compose -f ops/docker-compose.yml up -d
```

This starts:
- Qdrant (ports 6333, 6334)
- PostgreSQL (if configured)
- n8n (if configured)

## Step 4: Run the Application

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
- `CORTEX_DB_URL=postgresql+psycopg://cortex:cortex@localhost:5432/cortex`
- `PLAYWRIGHT_BROWSERS_PATH=$HOME/.cache/ms-playwright`

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

## Troubleshooting

### Nix daemon permission denied
Run: `./setup-nix.sh` then `newgrp nixbld`

### Flakes not enabled
Check: `cat ~/.config/nix/nix.conf` should contain `experimental-features = nix-command flakes`

### Playwright browsers not installing
Run: `pnpm exec playwright install --with-deps` inside the Nix shell

### Docker socket permission denied
Add user to docker group: `sudo usermod -aG docker $USER` then log out/in














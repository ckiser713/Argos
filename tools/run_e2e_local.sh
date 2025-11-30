#!/usr/bin/env bash
set -euo pipefail

# Local runner for Playwright E2E tests
# - Installs Playwright browsers (non-root or with deps)
# - Starts backend and frontend servers in background
# - Runs Playwright tests and cleans up

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Ensure script is run inside Nix dev shell
if [ -z "${IN_NIX_SHELL:-}" ]; then
  echo "ERROR: This script must be run inside the Nix dev shell."
  echo "Run: nix develop --command bash or run run_e2e_nix.sh to run the suite inside Nix."
  exit 1
fi

# Provide helpful instructions if run as non-interactive
if [ "$EUID" -ne 0 ]; then
  echo "Note: some host dependencies may require sudo. Run tools/install_playwright_deps.sh if needed."
fi

export CORTEX_SKIP_AUTH=1
export PLAYWRIGHT_BASE_URL=http://localhost:5173
export PLAYWRIGHT_API_BASE=http://127.0.0.1:8000
# For local E2E runs, allow tests to run without having real LLM models by
# mocking lanes availability. Tests requiring real models should set this to 0.
export CORTEX_E2E_MOCK_LANES=1

# Install Node deps
pnpm install --silent

# Ensure Poetry is using Python 3.11 for backend
"$ROOT_DIR/tools/ensure_python311_poetry.sh"

# Install Playwright browsers (use without --with-deps when inside Nix)
if [ -n "${IN_NIX_SHELL:-}" ]; then
  echo "Detected Nix shell; installing Playwright browsers without apt-based host deps"
  pnpm exec playwright install || true
else
  if ! pnpm exec playwright install --with-deps; then
    echo "Failed to install with system deps; trying browsers install only"
    pnpm exec playwright install || true
  fi
fi

# Optionally start Qdrant (useful if not running via Docker compose)
if ! docker-compose -f docker-compose.e2e.yml ps qdrant >/dev/null 2>&1 || ! docker-compose -f docker-compose.e2e.yml ps qdrant | grep -q "Up"; then
  echo "Starting Qdrant via docker-compose.e2e.yml..."
  docker-compose -f docker-compose.e2e.yml up -d qdrant
  echo "Waiting for Qdrant to be healthy..."
  for i in {1..60}; do
    if curl -sf http://127.0.0.1:6333/health >/dev/null 2>&1; then
      echo "Qdrant healthy"
      break
    fi
    sleep 1
  done
fi

# Ensure backend port isn't in use (kill stale uvicorn if present)
if lsof -i :8000 -t >/dev/null 2>&1; then
  FOUND_PID=$(lsof -i :8000 -t)
  echo "Port 8000 is in use by PID $FOUND_PID, attempting to kill if it's a uvicorn process..."
  ps -p $FOUND_PID -o comm= | grep -E "uvicorn|python" >/dev/null 2>&1 && kill $FOUND_PID || echo "Not a uvicorn/python process; leaving port as-is"
fi

# Start backend
cd "$ROOT_DIR/backend"
PYTHONPATH="$ROOT_DIR" poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$ROOT_DIR"

# Ensure frontend (5173) port isn't in use (kill stale vite if present)
if lsof -i :5173 -t >/dev/null 2>&1; then
  FOUND_PID=$(lsof -i :5173 -t)
  echo "Port 5173 is in use by PID $FOUND_PID, attempting to kill if it's a vite/node process..."
  ps -p $FOUND_PID -o comm= | grep -E "node|vite" >/dev/null 2>&1 && kill $FOUND_PID || echo "Not a node/vite process; leaving port as-is"
fi

# Start frontend
cd "$ROOT_DIR/frontend"
pnpm run preview -- --port 5173 --strictPort &
FRONTEND_PID=$!
cd "$ROOT_DIR"

# Wait for servers to be ready
echo "Waiting for backend and frontend to be ready..."
for i in {1..30}; do
  if curl -sS --fail http://127.0.0.1:8000/api/docs >/dev/null 2>&1 && curl -sS --fail http://127.0.0.1:5173/ >/dev/null 2>&1; then
    echo "Servers ready"
    break
  fi
  sleep 1
done
# Wait for servers to be ready
echo "Waiting for backend, frontend and Qdrant to be ready..."
for i in {1..60}; do
  if curl -sS --fail http://127.0.0.1:8000/api/docs >/dev/null 2>&1 && curl -sS --fail http://127.0.0.1:5173/ >/dev/null 2>&1 && curl -sS --fail http://127.0.0.1:6333/health >/dev/null 2>&1; then
    echo "Servers ready"
    break
  fi
  sleep 1
done

# Run Playwright tests (forward args if provided)
if [ $# -gt 0 ]; then
  pnpm exec playwright test "$@" || TEST_RC=$?
else
  pnpm exec playwright test || TEST_RC=$?
fi

# Cleanup
echo "Shutting down servers..."
kill $BACKEND_PID || true
kill $FRONTEND_PID || true
wait $BACKEND_PID 2>/dev/null || true
wait $FRONTEND_PID 2>/dev/null || true

if [ -n "${TEST_RC:-}" ]; then
  exit $TEST_RC
fi

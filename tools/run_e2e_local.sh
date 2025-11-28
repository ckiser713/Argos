#!/usr/bin/env bash
set -euo pipefail

# Local runner for Playwright E2E tests
# - Installs Playwright browsers (non-root or with deps)
# - Starts backend and frontend servers in background
# - Runs Playwright tests and cleans up

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

# Provide helpful instructions if run as non-interactive
if [ "$EUID" -ne 0 ]; then
  echo "Note: some host dependencies may require sudo. Run tools/install_playwright_deps.sh if needed."
fi

export CORTEX_SKIP_AUTH=1
export PLAYWRIGHT_BASE_URL=http://localhost:5173
export PLAYWRIGHT_API_BASE=http://127.0.0.1:8000

# Install Node deps
pnpm install --silent

# Ensure Poetry is using Python 3.11 for backend
"$ROOT_DIR/tools/ensure_python311_poetry.sh"

# Install Playwright browsers (attempt to add host deps if needed)
if ! pnpm exec playwright install --with-deps; then
  echo "Failed to install with system deps; trying browsers install only"
  pnpm exec playwright install
fi

# Start backend
cd "$ROOT_DIR/backend"
PYTHONPATH="$ROOT_DIR" poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$ROOT_DIR"

# Start frontend
cd "$ROOT_DIR/frontend"
pnpm run preview -- --port 5173 &
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

# Run Playwright tests
pnpm exec playwright test || TEST_RC=$?

# Cleanup
echo "Shutting down servers..."
kill $BACKEND_PID || true
kill $FRONTEND_PID || true
wait $BACKEND_PID 2>/dev/null || true
wait $FRONTEND_PID 2>/dev/null || true

if [ -n "${TEST_RC:-}" ]; then
  exit $TEST_RC
fi

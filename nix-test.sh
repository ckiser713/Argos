#!/usr/bin/env bash
set -euo pipefail

# Nix-based deployment test runner:
# - nix flake check
# - Smoke checks (backend, vLLM, llama.cpp, Qdrant)
# - Backend pytest
# - Frontend unit tests
# - Playwright (requires PLAYWRIGHT_BASE_URL)
#
# Env overrides:
#   ENV_FILE=ops/cortex.env
#   BASE_URL_BACKEND=http://localhost:8000
#   VLLM_URL=http://localhost:8000
#   LLAMA_SR_URL=http://localhost:8080
#   QDRANT_URL=http://localhost:6333
#   PLAYWRIGHT_BASE_URL=http://localhost:5173

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/ops/cortex.env}"
BASE_URL_BACKEND="${BASE_URL_BACKEND:-http://localhost:8000}"
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
LLAMA_SR_URL="${LLAMA_SR_URL:-http://localhost:8080}"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://localhost:5173}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE"
  echo "Set ENV_FILE or create ops/cortex.env"
  exit 1
fi

echo "=== nix flake check ==="
cd "$ROOT_DIR"
nix flake check

echo "=== Smoke checks ==="
BASE_URL_BACKEND="$BASE_URL_BACKEND" \
VLLM_URL="$VLLM_URL" \
LLAMA_SR_URL="$LLAMA_SR_URL" \
QDRANT_URL="$QDRANT_URL" \
./ops/smoke.sh

echo "=== Backend: pytest ==="
nix develop -f "$ROOT_DIR/flake.nix" --command bash -lc "cd backend && poetry run pytest"

echo "=== Frontend: unit tests ==="
nix develop -f "$ROOT_DIR/flake.nix" --command bash -lc "cd frontend && pnpm install --frozen-lockfile && pnpm test"

echo "=== Frontend: Playwright (integration) ==="
nix develop -f "$ROOT_DIR/flake.nix" --command bash -lc "cd frontend && PLAYWRIGHT_BASE_URL='$PLAYWRIGHT_BASE_URL' pnpm exec playwright test --project chromium"

echo "All checks completed."

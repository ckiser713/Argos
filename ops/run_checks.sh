#!/usr/bin/env bash
set -euo pipefail

# Unified gate for smoke + tests. Requires services up:
# - Postgres (see ops/docker-compose.yml)
# - Qdrant
# - n8n
# - vLLM / llama.cpp lanes reachable at configured URLs

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Smoke ==="
(
  cd "$ROOT_DIR"
  BASE_URL_BACKEND="${BASE_URL_BACKEND:-http://localhost:8000}" \
  VLLM_URL="${VLLM_URL:-http://localhost:8000}" \
  LLAMA_SR_URL="${LLAMA_SR_URL:-http://localhost:8080}" \
  QDRANT_URL="${QDRANT_URL:-http://localhost:6333}" \
  ./ops/smoke.sh
)

echo "=== Backend tests ==="
(
  cd "$ROOT_DIR/backend"
  poetry run pytest
)

echo "=== Frontend unit tests ==="
(
  cd "$ROOT_DIR/frontend"
  pnpm install --frozen-lockfile
  pnpm test
)

echo "=== Playwright (integration) ==="
(
  cd "$ROOT_DIR/frontend"
  : "${PLAYWRIGHT_BASE_URL:?Set PLAYWRIGHT_BASE_URL to the deployed frontend URL}"
  pnpm exec playwright test --project chromium
)

echo "All checks passed."

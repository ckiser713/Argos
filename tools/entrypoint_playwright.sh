#!/usr/bin/env bash
set -euo pipefail

# Entrypoint wrapper for Playwright in Docker Compose
# - Install deps and Playwright browsers
# - Run tests
# - Ensure any lingering Playwright 'show-report' server is killed
# - Exit with the test exit code so Compose --abort-on-container-exit can stop other services

ROOT_DIR=/work
cd "$ROOT_DIR"

export CORTEX_SKIP_AUTH=1

PLAYWRIGHT_BASE_URL="${PLAYWRIGHT_BASE_URL:-http://frontend:5173}"
PLAYWRIGHT_API_BASE="${PLAYWRIGHT_API_BASE:-http://backend:8000/api}"

if [ "${PLAYWRIGHT_SKIP_INSTALL:-0}" != "1" ]; then
  pnpm install --silent
  if ! pnpm exec playwright install --with-deps; then
    pnpm exec playwright install
  fi
fi

wait_for_url() {
  url="$1"
  name="$2"
  max_attempts="${3:-60}"
  sleep_seconds="${4:-2}"
  echo "Waiting for ${name} at ${url} ..."
  for i in $(seq 1 "$max_attempts"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "✓ ${name} ready"
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "✗ ${name} not ready after $max_attempts attempts"
  return 1
}

API_READY_URL="${PLAYWRIGHT_API_BASE%/}/system/ready"
FRONTEND_URL="${PLAYWRIGHT_BASE_URL%/}/"

wait_for_url "$API_READY_URL" "backend readiness" 60 2
wait_for_url "$FRONTEND_URL" "frontend" 60 2

set +e
PLAYWRIGHT_TEST_ARGS=${PLAYWRIGHT_TEST_ARGS:-"--timeout=60000 --reporter=list --reporter=html"}
pnpm exec playwright test $PLAYWRIGHT_TEST_ARGS
TEST_RC=$?
set -e

# Kill any Playwright report server that might have been launched
pkill -f "playwright show-report" || true
pkill -f "playwright serve" || true
pkill -f "playwright" || true

exit $TEST_RC

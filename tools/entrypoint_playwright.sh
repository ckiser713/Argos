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

pnpm install --silent
if ! pnpm exec playwright install --with-deps; then
  pnpm exec playwright install
fi

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

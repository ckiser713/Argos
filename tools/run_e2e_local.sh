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
export CORTEX_ENV=local
export PLAYWRIGHT_BASE_URL=http://localhost:5173
export PLAYWRIGHT_API_BASE=http://127.0.0.1:8000/api
export CORTEX_ATLAS_DB_PATH="${CORTEX_ATLAS_DB_PATH:-$ROOT_DIR/test_atlas.db}"
# For local E2E runs, allow tests to run without having real LLM models by
# mocking lanes availability. Tests requiring real models should set this to 0.
export CORTEX_E2E_MOCK_LANES=1
export CORTEX_STORAGE_BACKEND=s3
export CORTEX_STORAGE_ENDPOINT_URL=http://127.0.0.1:9000
export CORTEX_STORAGE_BUCKET=cortex-ingest
export CORTEX_STORAGE_ACCESS_KEY=minioadmin
export CORTEX_STORAGE_SECRET_KEY=minioadmin
export CORTEX_STORAGE_SECURE=false
export CORTEX_QDRANT_URL=http://127.0.0.1:6333
export CORTEX_CELERY_BROKER_URL=redis://127.0.0.1:6379/0
export CORTEX_CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
export CORTEX_TASKS_EAGER=false

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

wait_for_redis() {
  max_attempts="${1:-60}"
  sleep_seconds="${2:-2}"
  echo "Waiting for redis (localhost:6379) ..."
  for i in $(seq 1 "$max_attempts"); do
    if docker-compose -f docker-compose.e2e.yml exec -T redis redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; then
      echo "✓ redis ready"
      return 0
    fi
    sleep "$sleep_seconds"
  done
  echo "✗ redis not ready after $max_attempts attempts"
  return 1
}

bootstrap_minio_bucket() {
  echo "Ensuring MinIO bucket ${CORTEX_STORAGE_BUCKET} exists..."
  PYTHONPATH="$ROOT_DIR" poetry run python - <<'PY'
import os
import boto3
from botocore.config import Config

endpoint = os.environ.get("CORTEX_STORAGE_ENDPOINT_URL", "http://127.0.0.1:9000")
bucket = os.environ.get("CORTEX_STORAGE_BUCKET", "cortex-ingest")
access_key = os.environ.get("CORTEX_STORAGE_ACCESS_KEY", "minioadmin")
secret_key = os.environ.get("CORTEX_STORAGE_SECRET_KEY", "minioadmin")
use_ssl = os.environ.get("CORTEX_STORAGE_SECURE", "false").lower() == "true"

session = boto3.session.Session()
s3 = session.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    use_ssl=use_ssl,
    config=Config(s3={"addressing_style": "path"}),
)

try:
    s3.head_bucket(Bucket=bucket)
    print(f"✓ Bucket '{bucket}' already exists")
except Exception:
    s3.create_bucket(Bucket=bucket)
    print(f"✓ Bucket '{bucket}' created")
PY
}

initialize_db() {
  echo "Initializing test database schema..."
  PYTHONPATH="$ROOT_DIR" poetry run python - <<'PY'
from app.db import init_db

init_db()
print("✓ Database initialized")
PY
}

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

echo "Starting dependencies (qdrant, minio, redis) via docker-compose.e2e.yml..."
docker-compose -f docker-compose.e2e.yml up -d qdrant minio redis
wait_for_url http://127.0.0.1:6333/health "qdrant" 60 2
wait_for_url http://127.0.0.1:9000/minio/health/ready "minio" 60 2
wait_for_redis 60 2
bootstrap_minio_bucket
initialize_db

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

wait_for_url http://127.0.0.1:8000/api/system/ready "backend" 60 2
wait_for_url http://127.0.0.1:5173/ "frontend" 60 2
wait_for_url http://127.0.0.1:6333/health "qdrant" 60 2
wait_for_url http://127.0.0.1:9000/minio/health/ready "minio" 60 2

echo "Running preflight health checks..."
curl -sS --fail http://127.0.0.1:8000/api/system/health >/dev/null
curl -sS --fail http://127.0.0.1:8000/api/system/ready >/dev/null

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

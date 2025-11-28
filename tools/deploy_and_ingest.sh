#!/usr/bin/env bash
set -euo pipefail

# Deploy the project, ingest a takeout directory, and monitor ingest jobs.
# Usage: bash tools/deploy_and_ingest.sh [--takeout ~/takeout] [--with-inference] [--api-url http://127.0.0.1:8000]
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://127.0.0.1:8000}"
TAKEOUT_DIR="${TAKEOUT_DIR:-$HOME/takeout}"
WITH_INFERENCE=false

# Parse args
while [ $# -gt 0 ]; do
  case "$1" in
    --takeout) TAKEOUT_DIR="$2"; shift 2;;
    --api-url) API_URL="$2"; shift 2;;
    --with-inference) WITH_INFERENCE=true; shift;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

export CORTEX_SKIP_AUTH=1
cd "$ROOT_DIR" || exit 1

# Ensure Poetry uses Python 3.11 (installs backend deps if necessary)
if [ -f "$ROOT_DIR/tools/ensure_python311_poetry.sh" ]; then
  bash "$ROOT_DIR/tools/ensure_python311_poetry.sh"
fi

# Optionally start inference engine and qdrant using ops/docker-compose.yml
if [ "$WITH_INFERENCE" = "true" ]; then
  echo "Starting inference stack (Qdrant + inference engine) via ops/docker-compose.yml..."
  set +e
  (cd "$ROOT_DIR/ops" && docker-compose up -d)
  CI=$?
  set -e
  if [ "$CI" -ne 0 ]; then
    echo "⚠ Failed to start the full inference engine via ops/docker-compose.yml (image/build not found)."
    echo "⚠ Continuing without inference engine; attempting to start qdrant only."
    set +e
    (cd "$ROOT_DIR/ops" && docker-compose up -d qdrant) || true
    set -e
  fi
  echo "Waiting for Qdrant to become healthy..."
  for i in {1..60}; do
    if curl -sS --fail http://localhost:6333/health >/dev/null 2>&1 ; then
      echo "Qdrant ready"
      break
    fi
    echo "Waiting for Qdrant..."
    sleep 2
  done
fi

# Start backend & frontend via compose file if present
if [ -f "$ROOT_DIR/docker-compose.e2e.yml" ]; then
  echo "Starting backend and frontend via docker-compose.e2e.yml..."
  docker-compose -f "$ROOT_DIR/docker-compose.e2e.yml" up --build -d
else
  echo "No docker-compose.e2e.yml found. Using ops/docker-compose.yml to start qdrant only."
fi

# Wait for backend readiness
echo "Waiting for backend readiness at $API_URL/api/docs..."
for i in {1..60}; do
  if curl -sS --fail "$API_URL/api/docs" >/dev/null 2>&1; then
    echo "Backend ready"
    break
  fi
  sleep 2
done

# Wait for frontend
echo "Waiting for frontend readiness at http://localhost:5173..."
for i in {1..60}; do
  if curl -sS --fail http://localhost:5173/ >/dev/null 2>&1; then
    echo "Frontend ready"
    break
  fi
  sleep 2
done

# Verify takeout path
if [ ! -d "$TAKEOUT_DIR" ]; then
  echo "Takeout directory does not exist: $TAKEOUT_DIR"
  exit 1
fi

# Run the inject script (uses the backend HTTP API)
if [ -f "$ROOT_DIR/backend/scripts/inject_takeout_api.py" ]; then
  echo "Starting upload/injection of $TAKEOUT_DIR to $API_URL..."
  if command -v poetry >/dev/null 2>&1; then
    (cd "$ROOT_DIR/backend" && poetry run python scripts/inject_takeout_api.py "$TAKEOUT_DIR" --api-url "$API_URL")
  else
    python3 "$ROOT_DIR/backend/scripts/inject_takeout_api.py" "$TAKEOUT_DIR" --api-url "$API_URL"
  fi
else
  echo "inject_takeout_api.py script not found in backend/scripts. Aborting ingest step."
  exit 1
fi

# Get a project ID created by the ingest (if any)
PROJECT_ID="$(python3 - <<PY
import requests, os
api = os.environ.get('API_URL', '${API_URL}')
try:
    r = requests.get(f"{api}/api/projects")
    r.raise_for_status()
    data = r.json()
    items = data.get('items') or data
    # try to find a project with `takeout` in its name
    for p in (items or []):
        name = p.get('name','').lower()
        if 'takeout' in name or name.startswith('takeout import'):
            print(p.get('id'))
            raise SystemExit(0)
    if items:
        print(items[0].get('id'))
except Exception:
    pass
print('')
PY
)"

if [ -z "$PROJECT_ID" ]; then
  echo "Could not determine Project ID. Check the API and created projects." 
else
  echo "Monitoring ingest jobs for project: $PROJECT_ID..."
  # Poll the ingest jobs and wait until none are RUNNING
    while true; do
    sleep 8
    read -r running statuses <<< $(python3 - <<PY
  import requests,os,json
  api=os.environ.get('API_URL','${API_URL}')
  pid='${PROJECT_ID}'
  try:
    r = requests.get(f"{api}/api/projects/{pid}/ingest/jobs")
    r.raise_for_status()
    items = r.json().get('items') or r.json()
    stat = {}
    for j in (items or []):
      s = j.get('status','UNKNOWN')
      stat[s] = stat.get(s,0)+1
    running = stat.get('RUNNING',0) + stat.get('PENDING',0)
    print(str(running), json.dumps(stat))
  except Exception as e:
    print('1', json.dumps({'error': str(e)}))
PY
  )
    echo "Ingest job statuses: $statuses"
    if [ "$running" -eq 0 ]; then
      echo "No running ingest jobs"
      break
    fi
    done
fi

echo "Deployment and ingestion completed. You can monitor logs:"
echo "  tail -f .logs/backend.log"
echo "  docker-compose -f docker-compose.e2e.yml logs -f --tail=200"

exit 0

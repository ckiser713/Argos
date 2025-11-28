#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
PROJECT_ID="${PROJECT_ID:-}"

function check_endpoint() {
  local url="$1"
  local label="$2"
  if curl -sS --fail "$url" >/dev/null 2>&1; then
    printf "%s: OK\n" "$label"
  else
    printf "%s: FAILED\n" "$label"
  fi
}

echo "Monitoring endpoints: $API_URL (backend), Qdrant (http://localhost:6333/health), frontend (http://localhost:5173/)"
while true; do
  echo "---- $(date -u) ----"
  check_endpoint "$API_URL/api/docs" "Backend (docs)"
  check_endpoint "http://localhost:6333/health" "Qdrant"
  check_endpoint "http://localhost:5173" "Frontend"

  # Get project id if not provided
  if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(python3 - <<PY
import requests,os,sys
api=os.environ.get('API_URL','${API_URL}')
try:
    resp=requests.get(f"{api}/api/projects?limit=1")
    resp.raise_for_status()
    data=resp.json()
    items=data.get('items') or data
    if items:
        print(items[0].get('id'))
        sys.exit(0)
except Exception:
    pass
print('')
sys.exit(1)
PY
)
  fi

  if [ -n "$PROJECT_ID" ]; then
    echo "Project: $PROJECT_ID"
    python3 - <<PY
import requests,os,json
api=os.environ.get('API_URL','${API_URL}')
pid='${PROJECT_ID}'
try:
    jresp=requests.get(f"{api}/api/projects/{pid}/ingest/jobs")
    arresp=requests.get(f"{api}/api/projects/{pid}/agent-runs")
    if jresp.status_code==200:
        items=jresp.json().get('items') or jresp.json()
        print('Ingest jobs:', len(items))
        status_counts={}
        for j in (items or []):
            s=j.get('status','UNKNOWN')
            status_counts[s]=status_counts.get(s,0)+1
        print('Ingest by status:', status_counts)
    else:
        print('Ingest query failed', jresp.status_code)
    if arresp.status_code==200:
        items2=arresp.json().get('items') or arresp.json()
        print('Agent runs:', len(items2))
    else:
        print('Agent run query failed', arresp.status_code)
except Exception as e:
    print('Error querying project endpoints:', e)
PY
  fi

  # Tail last 10 lines of backend log if available
  if [ -f ".logs/backend.log" ]; then
    echo "---- backend log (last 10 lines) ----"
    tail -n 10 .logs/backend.log | sed -e 's/^/    /'
  fi

  echo ""
  sleep 8
done

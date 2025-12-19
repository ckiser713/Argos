#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Load overrides early
BACKUP_ENV_FILE=${BACKUP_ENV_FILE:-/etc/cortex/backup.env}
[[ -f "$BACKUP_ENV_FILE" ]] && source "$BACKUP_ENV_FILE"

# Defaults
BACKUP_ROOT=${BACKUP_ROOT:-/var/backups/cortex}
BACKUP_LOG_FILE=${BACKUP_LOG_FILE:-/var/log/cortex/backup.log}
BACKUP_REMOTE=${BACKUP_REMOTE:-}          # e.g. user@backup-host:/backups/cortex
RSYNC_ARGS=${RSYNC_ARGS:-"-az --delete"}  # used when BACKUP_REMOTE is set

POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-cortex-postgres}
POSTGRES_DB=${POSTGRES_DB:-cortex}
POSTGRES_USER=${POSTGRES_USER:-cortex}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-}
POSTGRES_HOST=${POSTGRES_HOST:-}  # leave empty to use docker exec
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_RETENTION_DAYS=${POSTGRES_RETENTION_DAYS:-7}

QDRANT_CONTAINER=${QDRANT_CONTAINER:-cortex-qdrant}
QDRANT_HTTP=${QDRANT_HTTP:-http://localhost:6333}
QDRANT_RETENTION_DAYS=${QDRANT_RETENTION_DAYS:-7}
CURL_IMAGE=${CURL_IMAGE:-curlimages/curl:8.5.0}

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${BACKUP_ROOT}/postgres" "${BACKUP_ROOT}/qdrant" "$(dirname "$BACKUP_LOG_FILE")"

log() {
  local level="$1"; shift
  local msg="$*"
  printf '%s [%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$level" "$msg" | tee -a "$BACKUP_LOG_FILE"
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log ERROR "Missing required command: $cmd"
    exit 1
  fi
}

trap 'log ERROR "Backup run failed (line ${BASH_LINENO[0]}). Check ${BACKUP_LOG_FILE}"; exit 1' ERR

require_cmd docker
require_cmd date
require_cmd find

backup_postgres() {
  log INFO "Starting Postgres backup (container=${POSTGRES_CONTAINER:-none}, db=${POSTGRES_DB})"
  local outfile="${BACKUP_ROOT}/postgres/postgres_${TIMESTAMP}.dump"
  local tmpfile="${outfile}.tmp"

  if [[ -n "${POSTGRES_HOST:-}" ]] && command -v pg_dump >/dev/null 2>&1; then
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump -Fc -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "$tmpfile"
  else
    docker ps --format '{{.Names}}' | grep -qx "${POSTGRES_CONTAINER}" || {
      log ERROR "Container ${POSTGRES_CONTAINER} not running; set POSTGRES_HOST if using non-container Postgres"
      return 1
    }
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "${POSTGRES_CONTAINER}" \
      pg_dump -Fc -U "${POSTGRES_USER}" "${POSTGRES_DB}" > "$tmpfile"
  fi

  if command -v pg_restore >/dev/null 2>&1; then
    pg_restore --list "$tmpfile" >/dev/null
  else
    log WARN "pg_restore not found on host; skipping Postgres dump verification"
  fi

  mv "$tmpfile" "$outfile"
  gzip -f "$outfile"
  log INFO "Postgres backup stored at ${outfile}.gz"
}

backup_qdrant() {
  log INFO "Starting Qdrant snapshot (container=${QDRANT_CONTAINER:-none})"
  docker ps --format '{{.Names}}' | grep -qx "${QDRANT_CONTAINER}" || {
    log ERROR "Container ${QDRANT_CONTAINER} not running"
    return 1
  }

  local snapshot_json snapshot_name
  snapshot_json=$(docker run --rm --network "container:${QDRANT_CONTAINER}" "${CURL_IMAGE}" \
    -s -X POST "${QDRANT_HTTP}/snapshots" -H "Content-Type: application/json")

  snapshot_name=$(python3 - <<'PY' <<<"$snapshot_json"
import json, sys
data = json.load(sys.stdin)
print(data.get("result", {}).get("name", ""))
PY
)

  if [[ -z "$snapshot_name" ]]; then
    log ERROR "Unable to parse Qdrant snapshot name from response: $snapshot_json"
    return 1
  fi

  local container_path="/qdrant/snapshots/${snapshot_name}"
  local dest="${BACKUP_ROOT}/qdrant/${snapshot_name}"

  docker cp "${QDRANT_CONTAINER}:${container_path}" "$dest"
  docker exec "${QDRANT_CONTAINER}" rm -f "$container_path" >/dev/null 2>&1 || true

  log INFO "Qdrant snapshot saved to ${dest}"
}

prune_backups() {
  log INFO "Pruning old backups (Postgres>${POSTGRES_RETENTION_DAYS}d, Qdrant>${QDRANT_RETENTION_DAYS}d)"
  while IFS= read -r file; do
    log INFO "Pruned Postgres backup ${file}"
    rm -f "$file"
  done < <(find "${BACKUP_ROOT}/postgres" -type f -mtime +"$((POSTGRES_RETENTION_DAYS - 1))" -print)

  while IFS= read -r file; do
    log INFO "Pruned Qdrant snapshot ${file}"
    rm -f "$file"
  done < <(find "${BACKUP_ROOT}/qdrant" -type f -mtime +"$((QDRANT_RETENTION_DAYS - 1))" -print)
}

sync_remote() {
  [[ -z "$BACKUP_REMOTE" ]] && return 0
  if ! command -v rsync >/dev/null 2>&1; then
    log ERROR "BACKUP_REMOTE is set but rsync is not installed; skipping remote sync"
    return 1
  fi
  log INFO "Syncing backups to ${BACKUP_REMOTE}"
  rsync ${RSYNC_ARGS} "${BACKUP_ROOT}/" "${BACKUP_REMOTE}/"
  log INFO "Remote sync complete"
}

log INFO "Backup run started"
backup_postgres
backup_qdrant
prune_backups
sync_remote
log INFO "Backup run complete"


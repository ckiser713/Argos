# Cortex Backup & Restore (Postgres + Qdrant)

## Strategy (defaults)
- Postgres: nightly `pg_dump -Fc` at 02:30 UTC, retained 7 days.
- Qdrant: nightly snapshot at 02:35 UTC (follows Postgres), retained 7 days.
- Storage: local `${BACKUP_ROOT:-/var/backups/cortex}/{postgres,qdrant}` with optional remote mirror via `BACKUP_REMOTE` (rsync over SSH).
- Logging: `${BACKUP_LOG_FILE:-/var/log/cortex/backup.log}` captures success/failure.

## What’s included
- `ops/backup/run_backups.sh` – one-shot backup runner (Postgres dump + Qdrant snapshot, pruning, optional rsync).
- `ops/backup/backup.env.example` – fill and copy to `/etc/cortex/backup.env`.
- `ops/backup/systemd/cortex-backup.service` and `.timer` – daily automation.

## Setup
1) Prepare paths  
   `sudo mkdir -p /var/backups/cortex /var/log/cortex /etc/cortex`
2) Configure env  
   `sudo cp ops/backup/backup.env.example /etc/cortex/backup.env`  
   Edit `/etc/cortex/backup.env` (set `POSTGRES_PASSWORD`, optional `BACKUP_REMOTE`, adjust retention). `chmod 600` the file.
3) Make script executable  
   `chmod +x /home/nexus/Argos_Chatgpt/ops/backup/run_backups.sh`

### Systemd timer (recommended)
```
sudo cp ops/backup/systemd/cortex-backup.service /etc/systemd/system/
sudo cp ops/backup/systemd/cortex-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cortex-backup.timer
systemctl list-timers | grep cortex-backup
```
Adjust `ExecStart`/`WorkingDirectory` in the service file if the repo lives elsewhere.

### Cron alternative
`15 2 * * * BACKUP_ENV_FILE=/etc/cortex/backup.env /home/nexus/Argos_Chatgpt/ops/backup/run_backups.sh >> /var/log/cortex/backup.log 2>&1`

### Manual run
`sudo BACKUP_ENV_FILE=/etc/cortex/backup.env /home/nexus/Argos_Chatgpt/ops/backup/run_backups.sh`

## Restore: Postgres
1) Pause writers (stop ingest jobs/backend if possible).  
2) Pick a dump: `ls /var/backups/cortex/postgres`.  
3) Restore (drops existing objects):  
`gunzip -c /var/backups/cortex/postgres/postgres_YYYYMMDDThhmmssZ.dump.gz | docker exec -i -e PGPASSWORD=$POSTGRES_PASSWORD cortex-postgres pg_restore --clean --if-exists -U cortex -d cortex`  
4) If connections block restore:  
`docker exec cortex-postgres psql -U cortex -d postgres -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='cortex';"`  
5) Bring services back up and run a smoke query.

## Restore: Qdrant
1) Stop writers to Qdrant (stop backend/ingest).  
2) Choose snapshot: `ls /var/backups/cortex/qdrant`.  
3) Copy it in: `docker cp /var/backups/cortex/qdrant/<snapshot> cortex-qdrant:/qdrant/snapshots/`  
4) Recover via the Qdrant API (using the curl helper image):  
`docker run --rm --network container:cortex-qdrant curlimages/curl:8.5.0 -s -X POST http://localhost:6333/snapshots/recover -H 'Content-Type: application/json' -d '{"location":"/qdrant/snapshots/<snapshot>","force":true}'`  
5) Restart backend/ingest and verify health:  
`docker run --rm --network container:cortex-qdrant curlimages/curl:8.5.0 -s http://localhost:6333/health`

## Disaster-day checklist
- Freeze writes: stop ingest jobs/backend, disable external hooks.
- Confirm latest backups: list `postgres/` and `qdrant/` under `${BACKUP_ROOT}` (and remote if configured).
- Restore Postgres first, then Qdrant.
- Start services in order: postgres → qdrant → backend → frontend/ingest jobs.
- Validate: app health endpoint, sample query, and search/vector fetch against expected records.
- Resume traffic, trigger a fresh backup run, and monitor logs (`backup.log`, `docker logs cortex-postgres/qdrant`).

## Notes & troubleshooting
- Remote copies: set `BACKUP_REMOTE` to an SSH target; ensure key-based auth and rsync installed.
- Logs live at `${BACKUP_LOG_FILE}`; systemd also appends there via unit configuration.
- Change retention via `POSTGRES_RETENTION_DAYS` and `QDRANT_RETENTION_DAYS`.
- Test a restore quarterly on a staging stack to validate backups end-to-end.


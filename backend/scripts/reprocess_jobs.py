#!/usr/bin/env python3
"""
Script to reprocess completed ingest jobs that were completed before embedding models were loaded.
This resets their status to 'queued' so they can be reprocessed with proper indexing.
"""

from app.domain.models import IngestStatus
from app.services.ingest_service import ingest_service
import sys
import sqlite3
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def reprocess_completed_jobs(project_id: str, limit: int = None, dry_run: bool = False):
    """Reprocess completed jobs by resetting their status to queued."""

    # Get all completed jobs for the project
    db_path = backend_dir.parent / "atlas.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    query = """
        SELECT id, project_id, status, message 
        FROM ingest_jobs 
        WHERE project_id = ? AND status = 'completed' AND deleted_at IS NULL
        ORDER BY created_at ASC
    """

    if limit:
        query += f" LIMIT {limit}"

    c.execute(query, (project_id,))
    jobs = c.fetchall()

    print(f"Found {len(jobs)} completed jobs to reprocess")

    if dry_run:
        print("\n[DRY RUN] Would reprocess:")
        for job_id, proj_id, status, message in jobs[:10]:
            print(f"  - {job_id[:8]}... ({status}): {message}")
        if len(jobs) > 10:
            print(f"  ... and {len(jobs) - 10} more")
        return

    # Reset status to queued
    updated = 0
    for job_id, proj_id, status, message in jobs:
        try:
            # Update status directly in database
            c.execute(
                "UPDATE ingest_jobs SET status = ?, progress = 0.0, message = ?, completed_at = NULL WHERE id = ?",
                ('queued', 'Queued for reprocessing', job_id)
            )
            updated += 1

        except Exception as e:
            print(f"Error updating {job_id[:8]}: {e}")

    conn.commit()
    conn.close()

    print(f"\n✅ Reset {updated} jobs to 'queued' status")
    print("Jobs will be processed by background tasks when the backend processes them.")
    print("Note: You may need to trigger processing via the API or wait for background tasks.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Reprocess completed ingest jobs")
    parser.add_argument("--project-id", required=True, help="Project ID")
    parser.add_argument("--limit", type=int,
                        help="Limit number of jobs to reprocess")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    args = parser.parse_args()

    reprocess_completed_jobs(
        args.project_id, limit=args.limit, dry_run=args.dry_run)

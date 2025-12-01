#!/usr/bin/env python3
"""
Script to reprocess completed ingest jobs via the API.
This resets their status and triggers reprocessing.
"""

import requests
import sys
import time
from typing import Optional

API_URL = "http://localhost:8000"


def get_auth_token() -> str:
    """Obtain an authentication token from the backend."""
    token_url = f"{API_URL}/api/token"
    data = {"username": "admin", "password": "password"}
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


def reprocess_jobs_via_api(project_id: str, limit: Optional[int] = None, batch_size: int = 100):
    """Reprocess completed jobs by resetting status via API."""

    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Get completed jobs
    url = f"{API_URL}/api/projects/{project_id}/ingest/jobs"
    params = {"status": "completed", "limit": limit or 10000}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    jobs = data.get("items", [])

    print(f"Found {len(jobs)} completed jobs")

    if not jobs:
        print("No jobs to reprocess")
        return

    # Reprocess in batches
    reprocessed = 0
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({len(batch)} jobs)...")

        for job in batch:
            job_id = job["id"]

            # We can't directly update via API, so we'll need to use the database
            # For now, let's trigger processing by creating a new job with the same source
            # Actually, better approach: use the ingest service directly

            try:
                # Import and use the service directly
                import sys
                from pathlib import Path
                backend_dir = Path(__file__).parent.parent
                sys.path.insert(0, str(backend_dir))

                from app.services.ingest_service import ingest_service
                import asyncio

                # Reset status in database
                import sqlite3
                db_path = backend_dir.parent / "atlas.db"
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute(
                    "UPDATE ingest_jobs SET status = ?, progress = 0.0, message = ?, completed_at = NULL WHERE id = ?",
                    ('queued', 'Queued for reprocessing', job_id)
                )
                conn.commit()
                conn.close()

                # Trigger processing
                loop = asyncio.get_event_loop()
                loop.run_until_complete(ingest_service.process_job(job_id))

                reprocessed += 1

                if reprocessed % 10 == 0:
                    print(f"  Reprocessed {reprocessed}/{len(jobs)} jobs...")
                    time.sleep(0.1)  # Small delay to avoid overwhelming

            except Exception as e:
                print(f"  Error reprocessing {job_id[:8]}: {e}")

    print(f"\n✅ Reprocessed {reprocessed} jobs")
    print("Jobs are now being processed with embedding models available.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Reprocess completed ingest jobs via API")
    parser.add_argument("--project-id", required=True, help="Project ID")
    parser.add_argument("--limit", type=int,
                        help="Limit number of jobs to reprocess")
    parser.add_argument("--batch-size", type=int, default=100,
                        help="Batch size for processing")

    args = parser.parse_args()

    reprocess_jobs_via_api(
        args.project_id, limit=args.limit, batch_size=args.batch_size)

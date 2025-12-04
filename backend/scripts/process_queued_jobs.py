#!/usr/bin/env python3
"""
Process queued ingest jobs for a given project using ingest_service.process_job.
Usage: poetry run python scripts/process_queued_jobs.py --project-id <PROJECT_ID> [--limit N] [--workers M]
"""
import sys
import asyncio
from pathlib import Path
from typing import List

# Add parent directory to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import db_session
from app.services.ingest_service import ingest_service


def get_queued_jobs(project_id: str, limit: int = 100) -> List[str]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id FROM ingest_jobs WHERE project_id = ? AND status = 'queued' AND deleted_at IS NULL ORDER BY created_at ASC LIMIT ?",
            (project_id, limit),
        ).fetchall()
        return [r["id"] for r in rows]


async def worker(job_id: str):
    try:
        await ingest_service.process_job(job_id)
        print(f"Processed job: {job_id[:8]}...")
    except Exception as e:
        print(f"Error processing job {job_id[:8]}: {e}")


async def process_jobs_async(job_ids: List[str], concurrency: int = 10):
    semaphore = asyncio.Semaphore(concurrency)

    async def sem_worker(jid: str):
        async with semaphore:
            await worker(jid)

    tasks = [sem_worker(jid) for jid in job_ids]
    await asyncio.gather(*tasks)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--workers', type=int, default=10)
    args = parser.parse_args()

    job_ids = get_queued_jobs(args.project_id, limit=args.limit)
    if not job_ids:
        print('No queued jobs found')
        return

    print(f'Processing {len(job_ids)} queued jobs with concurrency={args.workers}')
    asyncio.run(process_jobs_async(job_ids, concurrency=args.workers))


if __name__ == '__main__':
    main()

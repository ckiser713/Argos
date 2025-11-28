#!/usr/bin/env python3
"""
Wait for ingest jobs to finish for a project.
Usage: python scripts/wait_for_ingest_jobs.py --api-url http://localhost:8000 --project-id <id> --timeout 1800
"""
import argparse
import requests
import time


def get_job_counts(api_url: str, project_id: str):
    items = []
    cursor = None
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{api_url}/api/projects/{project_id}/ingest/jobs", params=params)
        resp.raise_for_status()
        data = resp.json()
        page_items = data.get('items') or []
        items.extend(page_items)
        cursor = data.get('nextCursor')
        if not cursor:
            break
    counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
    for j in items:
        s = j.get('status', '').lower()
        counts[s] = counts.get(s, 0) + 1
    return counts, len(items)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-url', default='http://localhost:8000')
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--interval', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()

    start = time.time()
    while True:
        counts, total = get_job_counts(args.api_url, args.project_id)
        print(f"Total jobs: {total}, counts: {counts}")
        running = counts.get('running', 0) + counts.get('queued', 0)
        if running == 0:
            print('All jobs finished')
            break
        if time.time() - start > args.timeout:
            print('Timeout reached')
            break
        time.sleep(args.interval)

    return

if __name__ == '__main__':
    main()

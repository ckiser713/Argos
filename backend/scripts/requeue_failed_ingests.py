#!/usr/bin/env python3
"""
Script to requeue failed ingest jobs for a project by creating new ingest jobs
with the same durable source_uri.

Usage: python scripts/requeue_failed_ingests.py --api-url http://localhost:8000 --project-id <project-id>
"""
import argparse
import requests
from typing import List


def list_failed_jobs(api_url: str, project_id: str, page_limit: int = 100) -> List[dict]:
    items = []
    cursor = None
    while True:
        params = {"limit": page_limit, "status": "failed"}
        if cursor:
            params["cursor"] = cursor
        resp = requests.get(f"{api_url}/api/projects/{project_id}/ingest/jobs", params=params)
        if resp.status_code != 200:
            raise SystemExit(f"Failed to list jobs: {resp.status_code} {resp.text}")
        data = resp.json()
        items.extend(data.get("items", []))
        cursor = data.get("nextCursor")
        if not cursor:
            break
    return items


def requeue_job(api_url: str, project_id: str, source_uri: str) -> dict:
    payload = {"source_uri": source_uri}
    resp = requests.post(f"{api_url}/api/projects/{project_id}/ingest/jobs", json=payload)
    if resp.status_code not in (200, 201):
        raise Exception(f"Failed to create job: {resp.status_code} {resp.text}")
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--project-id", required=True, help="Project ID")
    args = parser.parse_args()

    failed_jobs = list_failed_jobs(args.api_url, args.project_id)
    if not failed_jobs:
        print("No failed jobs found.")
        return

    print(f"Found {len(failed_jobs)} failed jobs. Requeueing...")
    requeued = 0
    for job in failed_jobs:
        source_uri = job.get("source_uri") or job.get("source_path") or job.get("original_filename")
        if not source_uri:
            print(f"Skipping job {job.get('id')} - no source uri found")
            continue
        try:
            created = requeue_job(args.api_url, args.project_id, source_uri)
            print(f"Requeued job {job.get('id')} -> new job {created.get('id')} source_uri={source_uri}")
            requeued += 1
        except Exception as e:
            print(f"Failed to requeue job {job.get('id')}: {e}")

    print(f"Done: requeued {requeued}/{len(failed_jobs)} jobs")


if __name__ == '__main__':
    main()

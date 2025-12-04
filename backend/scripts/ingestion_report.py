#!/usr/bin/env python3
"""
Script to generate a comparison report between files in ~/takeout and ingested files.

Usage: poetry run python scripts/ingestion_report.py [--takeout-path PATH] [--project-id PROJECT_ID]
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from collections import defaultdict

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy import text

from app.db import db_session, _is_using_postgresql
from app.database import get_sync_engine
from app.services.project_service import get_project_service
from app.services.qdrant_service import qdrant_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def count_files_in_takeout(takeout_path: Path) -> Dict[str, Any]:
    """Count all files in takeout directory recursively."""
    logger.info(f"Counting files in {takeout_path}...")
    
    total_files = 0
    file_types = defaultdict(int)
    total_size = 0
    
    if not takeout_path.exists():
        logger.warning(f"Takeout directory does not exist: {takeout_path}")
        return {
            "total_files": 0,
            "file_types": {},
            "total_size": 0
        }
    
    for file_path in takeout_path.rglob('*'):
        if file_path.is_file():
            total_files += 1
            suffix = file_path.suffix.lower() or 'no_extension'
            file_types[suffix] += 1
            try:
                total_size += file_path.stat().st_size
            except Exception:
                pass
    
    return {
        "total_files": total_files,
        "file_types": dict(file_types),
        "total_size": total_size
    }


def count_ingest_jobs(project_id: Optional[str] = None) -> Dict[str, int]:
    """Count ingest jobs from database."""
    logger.info("Counting ingest jobs from database...")
    
    if _is_using_postgresql():
        engine = get_sync_engine()
        with engine.connect() as conn:
            if project_id:
                result = conn.execute(
                    text("""
                        SELECT status, COUNT(*) as count
                        FROM ingest_jobs
                        WHERE project_id = :project_id
                        GROUP BY status
                    """),
                    {"project_id": project_id}
                )
            else:
                result = conn.execute(
                    text("""
                        SELECT status, COUNT(*) as count
                        FROM ingest_jobs
                        GROUP BY status
                    """)
                )
            
            counts = {}
            for row in result:
                counts[row.status] = row.count
            
            # Get total count
            if project_id:
                total_result = conn.execute(
                    text("SELECT COUNT(*) as count FROM ingest_jobs WHERE project_id = :project_id"),
                    {"project_id": project_id}
                )
            else:
                total_result = conn.execute(
                    text("SELECT COUNT(*) as count FROM ingest_jobs")
                )
            total = total_result.fetchone().count
            
            return {
                "total": total,
                "by_status": counts
            }
    else:
        # SQLite
        with db_session() as conn:
            if project_id:
                cursor = conn.execute(
                    "SELECT status, COUNT(*) as count FROM ingest_jobs WHERE project_id = ? GROUP BY status",
                    (project_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT status, COUNT(*) as count FROM ingest_jobs GROUP BY status"
                )
            
            counts = {}
            for row in cursor.fetchall():
                counts[row["status"]] = row["count"]
            
            # Get total count
            if project_id:
                total_cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM ingest_jobs WHERE project_id = ?",
                    (project_id,)
                )
            else:
                total_cursor = conn.execute("SELECT COUNT(*) as count FROM ingest_jobs")
            
            total = total_cursor.fetchone()["count"]
            
            return {
                "total": total,
                "by_status": counts
            }


def count_qdrant_documents(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Count documents/chunks in Qdrant."""
    logger.info("Counting documents in Qdrant...")
    
    if not qdrant_service.client:
        logger.warning("Qdrant client not available")
        return {
            "total_collections": 0,
            "total_points": 0,
            "by_collection": {}
        }
    
    try:
        collections = qdrant_service.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        total_points = 0
        by_collection = {}
        
        for collection_name in collection_names:
            try:
                collection_info = qdrant_service.client.get_collection(collection_name)
                point_count = collection_info.points_count
                total_points += point_count
                by_collection[collection_name] = point_count
            except Exception as e:
                logger.warning(f"Failed to get info for collection {collection_name}: {e}")
        
        return {
            "total_collections": len(collection_names),
            "total_points": total_points,
            "by_collection": by_collection
        }
    except Exception as e:
        logger.error(f"Failed to count Qdrant documents: {e}")
        return {
            "total_collections": 0,
            "total_points": 0,
            "by_collection": {}
        }


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def generate_report(takeout_path: Path, project_id: Optional[str] = None) -> None:
    """Generate and print the comparison report."""
    print("=" * 80)
    print("INGESTION COMPARISON REPORT")
    print("=" * 80)
    print()
    
    # Count files in takeout
    takeout_stats = count_files_in_takeout(takeout_path)
    print(f"📁 Files in ~/takeout:")
    print(f"   Total files: {takeout_stats['total_files']:,}")
    print(f"   Total size: {format_size(takeout_stats['total_size'])}")
    print(f"   File types: {len(takeout_stats['file_types'])} unique extensions")
    if takeout_stats['file_types']:
        print("   Top 10 file types:")
        sorted_types = sorted(takeout_stats['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]
        for ext, count in sorted_types:
            print(f"     {ext}: {count:,}")
    print()
    
    # Count ingest jobs
    job_stats = count_ingest_jobs(project_id)
    print(f"📊 Ingest Jobs:")
    print(f"   Total jobs created: {job_stats['total']:,}")
    print(f"   By status:")
    for status, count in sorted(job_stats['by_status'].items()):
        print(f"     {status}: {count:,}")
    print()
    
    # Count Qdrant documents
    qdrant_stats = count_qdrant_documents(project_id)
    print(f"🔍 Qdrant Documents:")
    print(f"   Total collections: {qdrant_stats['total_collections']}")
    print(f"   Total points (chunks): {qdrant_stats['total_points']:,}")
    if qdrant_stats['by_collection']:
        print(f"   Top 10 collections:")
        sorted_collections = sorted(qdrant_stats['by_collection'].items(), key=lambda x: x[1], reverse=True)[:10]
        for name, count in sorted_collections:
            print(f"     {name}: {count:,}")
    print()
    
    # Comparison
    print("=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    total_files = takeout_stats['total_files']
    total_jobs = job_stats['total']
    completed_jobs = job_stats['by_status'].get('completed', 0)
    failed_jobs = job_stats['by_status'].get('failed', 0)
    total_points = qdrant_stats['total_points']
    
    print(f"Files in takeout:        {total_files:,}")
    print(f"Ingest jobs created:     {total_jobs:,}")
    print(f"  Completed:             {completed_jobs:,}")
    print(f"  Failed:                 {failed_jobs:,}")
    print(f"Qdrant points (chunks):  {total_points:,}")
    print()
    
    # Calculate ratios
    if total_files > 0:
        job_ratio = (total_jobs / total_files) * 100
        print(f"Job creation rate:       {job_ratio:.1f}% ({total_jobs}/{total_files})")
    
    if total_jobs > 0:
        completion_ratio = (completed_jobs / total_jobs) * 100
        print(f"Completion rate:          {completion_ratio:.1f}% ({completed_jobs}/{total_jobs})")
    
    if completed_jobs > 0:
        chunks_per_job = total_points / completed_jobs
        print(f"Avg chunks per job:       {chunks_per_job:.1f}")
    
    print()
    
    # Discrepancies
    print("=" * 80)
    print("DISCREPANCIES")
    print("=" * 80)
    
    if total_files > total_jobs:
        diff = total_files - total_jobs
        print(f"⚠️  {diff:,} files not processed (no ingest job created)")
    
    if total_jobs > completed_jobs + failed_jobs:
        pending = total_jobs - completed_jobs - failed_jobs
        print(f"⏳ {pending:,} jobs still pending/running")
    
    if failed_jobs > 0:
        print(f"❌ {failed_jobs:,} jobs failed")
    
    if completed_jobs > 0 and total_points == 0:
        print(f"⚠️  Jobs completed but no Qdrant points found")
    
    print()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate ingestion comparison report",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--takeout-path",
        type=str,
        default=str(Path.home() / "takeout"),
        help="Path to takeout directory (default: ~/takeout)"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project ID to filter by (optional)"
    )
    
    args = parser.parse_args()
    
    takeout_path = Path(args.takeout_path).expanduser()
    
    if not takeout_path.exists():
        logger.error(f"Takeout directory does not exist: {takeout_path}")
        sys.exit(1)
    
    generate_report(takeout_path, args.project_id)


if __name__ == "__main__":
    main()


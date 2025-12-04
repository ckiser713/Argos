#!/usr/bin/env python3
"""
Script to verify ingested documents are searchable, metadata preserved, and embeddings generated correctly.

Usage: poetry run python scripts/verify_data_integrity.py [--project-id PROJECT_ID]
"""

import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from app.db import init_db
from app.services.ingest_service import ingest_service
from app.services.qdrant_service import qdrant_service
from app.services.rag_service import rag_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_ingested_documents(project_id: Optional[str] = None) -> dict:
    """Verify ingested documents are searchable and have correct metadata."""
    logger.info("Verifying ingested documents...")
    
    init_db()
    
    results = {
        "jobs_with_metadata": 0,
        "jobs_without_metadata": 0,
        "searchable_documents": 0,
        "documents_with_embeddings": 0,
        "errors": []
    }
    
    try:
        # Get completed ingest jobs
        jobs = ingest_service.list_jobs(cursor=None, limit=100)
        completed_jobs = [j for j in jobs.items if j.status.value == 'completed']
        
        logger.info(f"Found {len(completed_jobs)} completed ingest jobs")
        
        # Check metadata preservation
        for job in completed_jobs[:10]:  # Sample first 10
            if job.metadata:
                results["jobs_with_metadata"] += 1
            else:
                results["jobs_without_metadata"] += 1
        
        # Check Qdrant collections
        if qdrant_service.client:
            collections = qdrant_service.client.get_collections().collections
            logger.info(f"Found {len(collections)} Qdrant collections")
            
            for collection in collections[:5]:  # Sample first 5 collections
                try:
                    info = qdrant_service.client.get_collection(collection.name)
                    if info.points_count > 0:
                        results["documents_with_embeddings"] += info.points_count
                        
                        # Try a simple search
                        try:
                            # Get a sample point to test search
                            search_result = qdrant_service.client.scroll(
                                collection_name=collection.name,
                                limit=1
                            )
                            if search_result[0]:
                                results["searchable_documents"] += 1
                        except Exception as e:
                            results["errors"].append(f"Search test failed for {collection.name}: {e}")
                            
                except Exception as e:
                    results["errors"].append(f"Failed to get info for {collection.name}: {e}")
        else:
            results["errors"].append("Qdrant client not available")
        
        # Test RAG service search
        try:
            if rag_service:
                # Try a simple search query
                search_results = rag_service.search("test", limit=1, project_id=project_id)
                if search_results:
                    logger.info("✓ RAG service search is working")
                else:
                    logger.info("⚠ RAG service search returned no results (may be normal if no data)")
        except Exception as e:
            results["errors"].append(f"RAG service search test failed: {e}")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        results["errors"].append(str(e))
    
    return results


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify ingested documents are searchable and embeddings are generated correctly"
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project ID to filter by (optional)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DATA INTEGRITY VERIFICATION")
    print("=" * 80)
    print()
    
    results = verify_ingested_documents(args.project_id)
    
    print("Verification Results:")
    print(f"  Jobs with metadata: {results['jobs_with_metadata']}")
    print(f"  Jobs without metadata: {results['jobs_without_metadata']}")
    print(f"  Searchable documents: {results['searchable_documents']}")
    print(f"  Documents with embeddings: {results['documents_with_embeddings']}")
    
    if results["errors"]:
        print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")
    else:
        print("\n✓ No errors encountered")
    
    print()


if __name__ == "__main__":
    main()


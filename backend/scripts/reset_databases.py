#!/usr/bin/env python3
"""
Script to reset all databases used by Cortex.
Resets PostgreSQL, Qdrant, SQLite, and optionally ChromaDB and Neo4j.

Usage: poetry run python scripts/reset_databases.py [--confirm]
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import sqlite3
from typing import Optional

from sqlalchemy import text
from qdrant_client import QdrantClient

from app.db import init_db, _is_using_postgresql, _db_path, db_session, Base
from app.database import get_sync_engine
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reset_postgresql() -> bool:
    """Reset PostgreSQL database by dropping all tables."""
    try:
        logger.info("Resetting PostgreSQL database...")
        engine = get_sync_engine()
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ Dropped all PostgreSQL tables")
        
        # Reinitialize schema
        init_db()
        logger.info("✓ Reinitialized PostgreSQL schema")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to reset PostgreSQL: {e}")
        return False


def reset_sqlite() -> bool:
    """Reset SQLite database by dropping all tables or deleting the file."""
    try:
        logger.info("Resetting SQLite database...")
        db_path = _db_path()
        
        if db_path.exists():
            # Drop all tables
            with db_session() as conn:
                # Get all table names
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = [row["name"] for row in cursor.fetchall()]
                
                # Drop each table
                for table in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.commit()
            
            logger.info(f"✓ Dropped all SQLite tables from {db_path}")
        else:
            logger.info(f"✓ SQLite database file does not exist: {db_path}")
        
        # Reinitialize schema
        init_db()
        logger.info("✓ Reinitialized SQLite schema")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to reset SQLite: {e}")
        return False


def reset_qdrant() -> bool:
    """Reset Qdrant by deleting all collections."""
    try:
        logger.info("Resetting Qdrant...")
        settings = get_settings()
        qdrant_url = getattr(settings, "qdrant_url", "http://localhost:6333")
        
        client = QdrantClient(url=qdrant_url)
        
        # Get all collections
        collections = client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if not collection_names:
            logger.info("✓ No Qdrant collections to delete")
            return True
        
        # Delete each collection
        for name in collection_names:
            try:
                client.delete_collection(collection_name=name)
                logger.info(f"  Deleted collection: {name}")
            except Exception as e:
                logger.warning(f"  Failed to delete collection {name}: {e}")
        
        logger.info(f"✓ Deleted {len(collection_names)} Qdrant collections")
        return True
    except Exception as e:
        logger.warning(f"⚠ Failed to reset Qdrant (may not be running): {e}")
        return False


def reset_chromadb() -> bool:
    """Reset ChromaDB if available."""
    try:
        logger.info("Resetting ChromaDB...")
        # Try to import and use ChromaDB service if available
        try:
            from app.services.chromadb_service import chromadb_service
            if hasattr(chromadb_service, 'reset_database'):
                result = chromadb_service.reset_database()
                if result:
                    logger.info("✓ ChromaDB reset successful")
                    return True
                else:
                    logger.warning("⚠ ChromaDB reset returned False")
                    return False
        except ImportError:
            logger.info("✓ ChromaDB service not available, skipping")
            return True
    except Exception as e:
        logger.warning(f"⚠ Failed to reset ChromaDB: {e}")
        return False


def reset_neo4j() -> bool:
    """Reset Neo4j if available."""
    try:
        logger.info("Resetting Neo4j...")
        # Try to import and use Neo4j service if available
        try:
            from app.services.neo4j_service import neo4j_service
            if hasattr(neo4j_service, 'clear_database'):
                result = neo4j_service.clear_database()
                if result:
                    logger.info("✓ Neo4j reset successful")
                    return True
                else:
                    logger.warning("⚠ Neo4j reset returned False")
                    return False
        except ImportError:
            logger.info("✓ Neo4j service not available, skipping")
            return True
    except Exception as e:
        logger.warning(f"⚠ Failed to reset Neo4j: {e}")
        return False


def main():
    """Main function to reset all databases."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset all databases used by Cortex",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt (use with caution!)"
    )
    
    args = parser.parse_args()
    
    if not args.confirm:
        response = input(
            "⚠️  WARNING: This will delete ALL data from all databases!\n"
            "Are you sure you want to continue? (yes/no): "
        )
        if response.lower() != "yes":
            logger.info("Reset cancelled by user")
            return
    
    logger.info("=" * 60)
    logger.info("Starting database reset...")
    logger.info("=" * 60)
    
    results = {}
    
    # Reset databases based on what's configured
    if _is_using_postgresql():
        results["PostgreSQL"] = reset_postgresql()
    else:
        results["SQLite"] = reset_sqlite()
    
    results["Qdrant"] = reset_qdrant()
    results["ChromaDB"] = reset_chromadb()
    results["Neo4j"] = reset_neo4j()
    
    # Summary
    logger.info("=" * 60)
    logger.info("Reset Summary:")
    logger.info("=" * 60)
    for db_name, success in results.items():
        status = "✓" if success else "✗"
        logger.info(f"{status} {db_name}")
    
    all_success = all(results.values())
    if all_success:
        logger.info("\n✓ All databases reset successfully!")
        sys.exit(0)
    else:
        logger.warning("\n⚠ Some databases failed to reset. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()


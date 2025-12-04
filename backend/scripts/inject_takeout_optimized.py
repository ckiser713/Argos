#!/usr/bin/env python3
"""
Optimized script to inject files from ~/takeout into the Cortex system.
Handles large batches (40k+ files) with:
- Async processing with concurrency control
- Progress tracking and checkpoint/resume
- Batch database operations
- Error handling that doesn't stop the process

Usage: poetry run python scripts/inject_takeout_optimized.py [takeout_path] [--project-id PROJECT_ID] [--extensions EXT ...] [--workers N] [--checkpoint FILE]
"""

import sys
import asyncio
import json
import shutil
from pathlib import Path
from typing import Optional, Set, Tuple
from datetime import datetime
import argparse

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from app.db import init_db
from app.domain.models import IngestRequest
from app.services.ingest_service import ingest_service
from app.services.project_service import ProjectService, get_project_service
from app.services.qdrant_service import qdrant_service

# Ensure embedding models are loaded
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verify Qdrant and embedding models are available
if not qdrant_service.client:
    logger.warning("Qdrant client not available. Files will be processed but not indexed.")
elif not qdrant_service.embedding_models.get('default'):
    logger.warning("Embedding models not loaded. Files will be processed but not indexed into Qdrant.")
    logger.info("Attempting to load embedding models...")
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        qdrant_service.embedding_models['default'] = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        qdrant_service.embedding_sizes['default'] = 384
        logger.info("✅ Embedding models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load embedding models: {e}")
else:
    logger.info("✅ Qdrant and embedding models are ready")


def get_or_create_default_project(service: ProjectService) -> str:
    """Get the first project or create a default one."""
    projects = service.list_projects(cursor=None, limit=1)
    if projects.items:
        return projects.items[0].id
    
    # Create a default project
    from app.domain.project import CreateProjectRequest
    project = service.create_project(CreateProjectRequest(
        name="Takeout Import",
        description="Files imported from takeout directory"
    ))
    return project.id


def should_exclude_file(file_path: Path) -> bool:
    """Check if a file should be excluded from ingestion."""
    # Exclude hidden files/directories
    if any(part.startswith('.') for part in file_path.parts):
        # Allow .gitignore, .env.example, etc. but exclude .git, .venv, etc.
        hidden_dirs = {'.git', '.svn', '.hg', '.venv', '.env', '.cache', '.idea', '.vscode', '.vs', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.tox', '.nox', '.coverage', '.ipynb_checkpoints'}
        if any(part in hidden_dirs for part in file_path.parts):
            return True
    
    # Exclude common build/cache directories
    exclude_dirs = {
        'node_modules', '__pycache__', 'venv', 'env', 'virtualenv',
        'build', 'dist', 'target', 'bin', 'obj', 'out', '.next', '.turbo',
        'coverage', 'htmlcov', '.eggs', '*.egg-info', 'videos', 'assets',
        'models', 'checkpoints', '.cache', 'tmp', 'temp'
    }
    if any(part in exclude_dirs for part in file_path.parts):
        return True
    
    # Exclude common build/cache file extensions
    exclude_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll', '.exe',
        '.DS_Store', 'Thumbs.db', '.tmp', '.temp', '.log', '.cache',
        '.lock', '.sqlite', '.db', '.egg-info'
    }
    if file_path.suffix.lower() in exclude_extensions:
        return True
    
    # Exclude .env files (but allow .env.example)
    if file_path.name.startswith('.env') and file_path.name != '.env.example':
        return True
    
    return False


def archive_excluded_file(file_path: Path, takeout_root: Path, archive_root: Path) -> bool:
    """Move an excluded file to the archive directory, preserving directory structure."""
    try:
        # Calculate relative path from takeout root
        try:
            relative_path = file_path.relative_to(takeout_root)
        except ValueError:
            # File is not under takeout root, use absolute path structure
            relative_path = Path('absolute') / file_path.parts[-3:]
        
        # Create archive destination path
        archive_path = archive_root / relative_path
        
        # Create parent directories
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file (or copy if move fails)
        try:
            shutil.move(str(file_path), str(archive_path))
        except Exception:
            # If move fails (e.g., cross-filesystem), try copy then delete
            shutil.copy2(str(file_path), str(archive_path))
            file_path.unlink()
        
        return True
    except Exception as e:
        print(f"  Warning: Failed to archive {file_path}: {e}", file=sys.stderr)
        return False


def find_files(directory: Path, extensions: Optional[list] = None, archive_root: Optional[Path] = None) -> Tuple[list[Path], int]:
    """Recursively find all files in directory, optionally filtered by extensions.
    
    Returns:
        Tuple of (files_to_ingest, archived_count)
    """
    files = []
    archived_count = 0
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        return files, 0
    
    if extensions:
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    print("Scanning directory (archiving build/temp/virtualenv files)...")
    if archive_root:
        archive_root.mkdir(parents=True, exist_ok=True)
        print(f"  Archive location: {archive_root}")
    
    for path in directory.rglob('*'):
        if path.is_file():
            # Archive excluded files
            if should_exclude_file(path):
                if archive_root:
                    if archive_excluded_file(path, directory, archive_root):
                        archived_count += 1
                        if archived_count % 100 == 0:
                            print(f"  Archived {archived_count} files...", end='\r')
                else:
                    archived_count += 1
                continue
            
            if not extensions or path.suffix.lower() in extensions:
                files.append(path)
        # Print progress every 1000 files found
        if len(files) % 1000 == 0 and len(files) > 0:
            print(f"  Found {len(files)} files (archived {archived_count})...", end='\r')
    
    print(f"\n  Total files to ingest: {len(files)}")
    print(f"  Files archived: {archived_count}")
    return sorted(files), archived_count


def load_checkpoint(checkpoint_file: Path) -> Set[str]:
    """Load processed file paths from checkpoint."""
    if not checkpoint_file.exists():
        return set()
    
    try:
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
            return set(data.get('processed_files', []))
    except Exception as e:
        print(f"Warning: Could not load checkpoint: {e}")
        return set()


def save_checkpoint(checkpoint_file: Path, processed_files: Set[str], stats: dict):
    """Save checkpoint with processed files and statistics."""
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump({
                'processed_files': list(processed_files),
                'stats': stats,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save checkpoint: {e}")


async def process_file_semaphore(semaphore, file_path: Path, project_id: str, file_index: int, total_files: int):
    """Process a single file with semaphore-controlled concurrency."""
    async with semaphore:
        try:
            abs_path = file_path.resolve()
            request = IngestRequest(source_path=str(abs_path))
            job = ingest_service.create_job(project_id=project_id, request=request)
            
            # Process the job asynchronously
            # Note: process_job is async, so we await it
            try:
                await ingest_service.process_job(job.id)
            except Exception as process_error:
                # Job was created but processing failed
                return {
                    'success': False,
                    'file': str(abs_path),
                    'job_id': job.id,
                    'error': f"Processing failed: {str(process_error)}",
                    'filename': file_path.name
                }
            
            return {
                'success': True,
                'file': str(abs_path),
                'job_id': job.id,
                'filename': file_path.name
            }
        except Exception as e:
            return {
                'success': False,
                'file': str(file_path.resolve()),
                'error': str(e),
                'filename': file_path.name
            }


async def inject_files_async(
    takeout_path: Path,
    project_id: Optional[str] = None,
    extensions: Optional[list] = None,
    max_workers: int = 10,
    checkpoint_file: Optional[Path] = None,
    archive_path: Optional[Path] = None
):
    """Inject all files from takeout_path into the system with async processing."""
    # Initialize database
    init_db()
    
    # Get or create project
    project_service = get_project_service()
    if not project_id:
        project_id = get_or_create_default_project(project_service)
        print(f"Using project: {project_id}")
    else:
        project = project_service.get_project(project_id)
        if not project:
            print(f"Error: Project {project_id} not found")
            return
        print(f"Using project: {project.name} ({project_id})")
    
    # Set up archive directory
    if archive_path is None:
        archive_path = takeout_path.parent / f"{takeout_path.name}_archive"
    
    # Find all files (and archive excluded ones)
    print(f"\nScanning {takeout_path} for files...")
    all_files, archived_count = find_files(takeout_path, extensions, archive_path)
    
    if not all_files:
        print("No files found to inject.")
        return
    
    print(f"\nFound {len(all_files)} files to inject.")
    
    # Load checkpoint if resuming
    processed_files = set()
    if checkpoint_file:
        processed_files = load_checkpoint(checkpoint_file)
        if processed_files:
            print(f"Resuming from checkpoint: {len(processed_files)} files already processed")
    
    # Filter out already processed files
    files_to_process = [
        f for f in all_files 
        if str(f.resolve()) not in processed_files
    ]
    
    if not files_to_process:
        print("All files have already been processed.")
        return
    
    print(f"Processing {len(files_to_process)} files ({len(processed_files)} already done)")
    print(f"Using {max_workers} concurrent workers\n")
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_workers)
    
    # Process files in batches with progress tracking
    results = []
    successful = 0
    failed = 0
    
    # Process in batches to save checkpoint periodically
    batch_size = 100
    for batch_start in range(0, len(files_to_process), batch_size):
        batch = files_to_process[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(files_to_process) + batch_size - 1) // batch_size
        
        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} files)...")
        
        # Create tasks for this batch
        tasks = [
            process_file_semaphore(
                semaphore,
                file_path,
                project_id,
                batch_start + i + 1,
                len(files_to_process)
            )
            for i, file_path in enumerate(batch)
        ]
        
        # Wait for batch to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in batch_results:
            if isinstance(result, Exception):
                failed += 1
                print(f"  ✗ Exception: {result}")
            elif result['success']:
                successful += 1
                processed_files.add(result['file'])
                if successful % 10 == 0:
                    print(f"  [{successful + failed}/{len(files_to_process)}] ✓ {result['filename'][:50]}...")
            else:
                failed += 1
                print(f"  ✗ {result['filename']}: {result.get('error', 'Unknown error')}")
        
        results.extend([r for r in batch_results if not isinstance(r, Exception)])
        
        # Save checkpoint after each batch
        if checkpoint_file:
            stats = {
                'total_files': len(all_files),
                'processed': len(processed_files),
                'successful': successful,
                'failed': failed,
                'remaining': len(files_to_process) - (successful + failed)
            }
            save_checkpoint(checkpoint_file, processed_files, stats)
            print(f"  Checkpoint saved: {successful} successful, {failed} failed")
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"Bulk Import Complete")
    print(f"{'='*60}")
    print(f"Total files found: {len(all_files)}")
    print(f"Files processed: {len(processed_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Project ID: {project_id}")
    
    if failed > 0:
        print(f"\n⚠️ {failed} files failed to process. Check errors above.")
    
    # Show job status summary
    print("\nChecking job statuses...")
    completed = 0
    running = 0
    queued = 0
    failed_jobs = 0
    
    for result in results:
        if result and result.get('success'):
            job = ingest_service.get_job(result['job_id'])
            if job:
                if job.status.value == "completed":
                    completed += 1
                elif job.status.value == "failed":
                    failed_jobs += 1
                elif job.status.value == "running":
                    running += 1
                else:
                    queued += 1
    
    print(f"  Completed: {completed}")
    print(f"  Running: {running}")
    print(f"  Queued: {queued}")
    print(f"  Failed: {failed_jobs}")


def main():
    parser = argparse.ArgumentParser(
        description="Optimized bulk import from takeout directory into Cortex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all files from ~/takeout with default settings
  python scripts/inject_takeout_optimized.py
  
  # Import with 20 concurrent workers
  python scripts/inject_takeout_optimized.py --workers 20
  
  # Import with checkpoint/resume capability
  python scripts/inject_takeout_optimized.py --checkpoint /tmp/takeout_checkpoint.json
  
  # Import only PDF and text files
  python scripts/inject_takeout_optimized.py --extensions pdf txt
  
  # Import into a specific project
  python scripts/inject_takeout_optimized.py --project-id <project-id>
        """
    )
    parser.add_argument(
        "takeout_path",
        nargs="?",
        default=str(Path.home() / "takeout"),
        help="Path to takeout directory (default: ~/takeout)"
    )
    parser.add_argument(
        "--project-id",
        help="Project ID to inject files into (default: first project or creates new one)"
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        help="File extensions to include (e.g., --extensions pdf txt md). If not specified, all files are included."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of concurrent workers (default: 10)"
    )
    parser.add_argument(
        "--checkpoint",
        help="Checkpoint file path for resume capability (default: no checkpoint)"
    )
    parser.add_argument(
        "--archive-path",
        type=str,
        help="Path to archive directory for excluded files (default: <takeout_path>_archive)"
    )
    
    try:
        args = parser.parse_args()
        
        takeout_path = Path(args.takeout_path).expanduser()
        
        if not takeout_path.exists():
            print(f"Error: Takeout directory does not exist: {takeout_path}", file=sys.stderr)
            print(f"Please create it or specify a different path.", file=sys.stderr)
            sys.exit(1)
        
        checkpoint_file = Path(args.checkpoint) if args.checkpoint else None
        archive_path = Path(args.archive_path).expanduser() if args.archive_path else None
        
        print(f"Starting optimized bulk import from: {takeout_path}")
        print(f"Concurrent workers: {args.workers}")
        if checkpoint_file:
            print(f"Checkpoint file: {checkpoint_file}")
        if archive_path:
            print(f"Archive directory: {archive_path}")
        
        # Run async function
        asyncio.run(inject_files_async(
            takeout_path,
            args.project_id,
            args.extensions,
            args.workers,
            checkpoint_file,
            archive_path
        ))
        
        print("\n✓ Bulk import process completed!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        if checkpoint_file:
            print(f"Checkpoint saved. Resume with: --checkpoint {checkpoint_file}", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Script to inject files from ~/takeout into the Cortex system.
Usage: poetry run python scripts/inject_takeout.py [takeout_path] [--project-id PROJECT_ID] [--extensions EXT ...]
"""

import sys
import shutil
from pathlib import Path
from typing import Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from app.db import init_db
from app.domain.models import IngestRequest
from app.services.ingest_service import ingest_service
from app.services.project_service import ProjectService, get_project_service


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


def find_files(directory: Path, extensions: Optional[list] = None, archive_root: Optional[Path] = None) -> tuple:
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


def inject_files(takeout_path: Path, project_id: Optional[str] = None, extensions: Optional[list] = None, archive_path: Optional[Path] = None):
    """Inject all files from takeout_path into the system."""
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
    files, archived_count = find_files(takeout_path, extensions, archive_path)
    
    if not files:
        print("No files found to inject.")
        return
    
    print(f"Found {len(files)} files to inject.")
    
    # Create ingest jobs for each file
    print("\nCreating ingest jobs...")
    job_ids = []
    for i, file_path in enumerate(files, 1):
        try:
            # Use absolute path
            abs_path = file_path.resolve()
            request = IngestRequest(source_path=str(abs_path))
            job = ingest_service.create_job(project_id=project_id, request=request)
            
            # Process the job (this extracts text and ingests into RAG)
            ingest_service.process_job(job.id)
            
            job_ids.append(job.id)
            print(f"[{i}/{len(files)}] ✓ {file_path.name} (job: {job.id[:8]}...)")
            sys.stdout.flush()  # Ensure output is flushed
        except Exception as e:
            print(f"[{i}/{len(files)}] ✗ {file_path.name} - Error: {e}")
            sys.stdout.flush()
    
    print(f"\n✓ Created {len(job_ids)} ingest jobs")
    print(f"  Project ID: {project_id}")
    print(f"  Jobs: {len(job_ids)}")
    
    # Show status summary
    print("\nChecking job statuses...")
    completed = 0
    failed = 0
    running = 0
    queued = 0
    
    for job_id in job_ids:
        job = ingest_service.get_job(job_id)
        if job:
            if job.status.value == "completed":
                completed += 1
            elif job.status.value == "failed":
                failed += 1
            elif job.status.value == "running":
                running += 1
            else:
                queued += 1
    
    print(f"  Completed: {completed}")
    print(f"  Running: {running}")
    print(f"  Queued: {queued}")
    print(f"  Failed: {failed}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Inject files from takeout directory into Cortex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inject all files from ~/takeout
  python scripts/inject_takeout.py
  
  # Inject files from a specific directory
  python scripts/inject_takeout.py /path/to/takeout
  
  # Inject only PDF and text files
  python scripts/inject_takeout.py --extensions pdf txt
  
  # Inject into a specific project
  python scripts/inject_takeout.py --project-id <project-id>
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
        
        archive_path = Path(args.archive_path).expanduser() if args.archive_path else None
        
        print(f"Starting file injection from: {takeout_path}")
        inject_files(takeout_path, args.project_id, args.extensions, archive_path)
        print("\n✓ Injection process completed!")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


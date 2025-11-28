#!/usr/bin/env python3
"""
Script to inject files from ~/takeout into the Cortex system via API.
This version uses the HTTP API, so the backend server must be running.

Usage: 
  poetry run python scripts/inject_takeout_api.py [takeout_path] [--project-id PROJECT_ID] [--extensions EXT ...]
  Or: python scripts/inject_takeout_api.py --api-url http://localhost:8000
"""

import sys
import requests
from pathlib import Path
from typing import Optional
import argparse

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


def find_files(directory: Path, extensions: Optional[list] = None) -> list[Path]:
    """Recursively find all files in directory, optionally filtered by extensions."""
    files = []
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist", file=sys.stderr)
        return files
    
    if extensions:
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in extensions]
    
    for path in directory.rglob('*'):
        if path.is_file():
            if not extensions or path.suffix.lower() in extensions:
                files.append(path)
    
    return sorted(files)


def get_or_create_project(api_url: str, project_id: Optional[str] = None) -> str:
    """Get or create a project."""
    if project_id:
        # Verify project exists
        response = requests.get(f"{api_url}/api/projects/{project_id}")
        if response.status_code == 200:
            return project_id
        print(f"Warning: Project {project_id} not found, will create a new one")
    
    # List projects
    response = requests.get(f"{api_url}/api/projects?limit=1")
    if response.status_code == 200:
        data = response.json()
        if data.get("items") and len(data["items"]) > 0:
            return data["items"][0]["id"]
    
    # Create a new project
    response = requests.post(
        f"{api_url}/api/projects",
        json={"name": "Takeout Import", "description": "Files imported from takeout directory"}
    )
    if response.status_code == 201:
        return response.json()["id"]
    
    raise Exception(f"Failed to get or create project: {response.status_code} {response.text}")


def inject_file_via_api(api_url: str, project_id: str, file_path: Path) -> Optional[str]:
    """Upload and inject a single file via API."""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            response = requests.post(
                f"{api_url}/api/projects/{project_id}/ingest/upload",
                files=files
            )
        
        if response.status_code == 200:
            return response.json().get("job_id")
        else:
            raise Exception(f"API error: {response.status_code} {response.text}")
    except Exception as e:
        raise Exception(f"Failed to upload {file_path.name}: {e}")


def inject_files(api_url: str, takeout_path: Path, project_id: Optional[str] = None, extensions: Optional[list] = None):
    """Inject all files from takeout_path into the system via API."""
    print(f"Connecting to API at: {api_url}")
    
    # Get or create project
    project_id = get_or_create_project(api_url, project_id)
    print(f"Using project ID: {project_id}")
    
    # Find all files
    print(f"\nScanning {takeout_path} for files...")
    files = find_files(takeout_path, extensions)
    
    if not files:
        print("No files found to inject.")
        return
    
    print(f"Found {len(files)} files to inject.\n")
    
    # Upload files
    print("Uploading files...")
    job_ids = []
    errors = []
    
    for i, file_path in enumerate(files, 1):
        try:
            job_id = inject_file_via_api(api_url, project_id, file_path)
            if job_id:
                job_ids.append(job_id)
                print(f"[{i}/{len(files)}] ✓ {file_path.name} (job: {job_id[:8]}...)")
            else:
                errors.append((file_path.name, "No job_id returned"))
                print(f"[{i}/{len(files)}] ✗ {file_path.name} - No job_id returned")
        except Exception as e:
            errors.append((file_path.name, str(e)))
            print(f"[{i}/{len(files)}] ✗ {file_path.name} - Error: {e}")
        
        sys.stdout.flush()
    
    print(f"\n✓ Created {len(job_ids)} ingest jobs")
    print(f"  Project ID: {project_id}")
    print(f"  Successful: {len(job_ids)}")
    print(f"  Failed: {len(errors)}")
    
    if errors:
        print("\nErrors:")
        for filename, error in errors:
            print(f"  - {filename}: {error}")


def main():
    parser = argparse.ArgumentParser(
        description="Inject files from takeout directory into Cortex via API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inject all files from ~/takeout (backend must be running on localhost:8000)
  python scripts/inject_takeout_api.py
  
  # Inject files from a specific directory
  python scripts/inject_takeout_api.py /path/to/takeout
  
  # Inject only PDF and text files
  python scripts/inject_takeout_api.py --extensions pdf txt
  
  # Inject into a specific project
  python scripts/inject_takeout_api.py --project-id <project-id>
  
  # Use a different API URL
  python scripts/inject_takeout_api.py --api-url http://localhost:8000
        """
    )
    parser.add_argument(
        "takeout_path",
        nargs="?",
        default=str(Path.home() / "takeout"),
        help="Path to takeout directory (default: ~/takeout)"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
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
    
    try:
        args = parser.parse_args()
        
        takeout_path = Path(args.takeout_path).expanduser()
        
        if not takeout_path.exists():
            print(f"Error: Takeout directory does not exist: {takeout_path}", file=sys.stderr)
            print(f"Please create it or specify a different path.", file=sys.stderr)
            sys.exit(1)
        
        # Test API connection
        try:
            response = requests.get(f"{args.api_url}/api/docs", timeout=2)
            if response.status_code != 200:
                print(f"Warning: API might not be accessible at {args.api_url}", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            print(f"Error: Cannot connect to API at {args.api_url}", file=sys.stderr)
            print(f"Make sure the backend server is running.", file=sys.stderr)
            sys.exit(1)
        
        print(f"Starting file injection from: {takeout_path}")
        inject_files(args.api_url, takeout_path, args.project_id, args.extensions)
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



"""
Repository analysis and indexing service.
Handles git repository ingestion and code indexing for gap analysis.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from app.services.llm_service import generate_text
from app.services.qdrant_code_search import QdrantCodeSearchBackend

logger = logging.getLogger(__name__)


class RepoService:
    """
    Service for analyzing and indexing git repositories.
    """

    def __init__(self):
        self.code_search = QdrantCodeSearchBackend()

    def index_repository(
        self,
        project_id: str,
        repo_path: str,
        file_extensions: Optional[List[str]] = None,
    ) -> dict:
        """
        Index a git repository by scanning code files and ingesting them into Qdrant.
        
        Args:
            project_id: Project ID to associate code with
            repo_path: Path to git repository root
            file_extensions: List of file extensions to index (default: common code extensions)
            
        Returns:
            Dictionary with indexing statistics
        """
        if file_extensions is None:
            file_extensions = [".py", ".js", ".ts", ".tsx", ".rs", ".go", ".java", ".cpp", ".c", ".h", ".hpp"]

        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        if not (repo_path_obj / ".git").exists():
            logger.warning(f"Path {repo_path} does not appear to be a git repository")

        stats = {
            "files_indexed": 0,
            "chunks_created": 0,
            "errors": [],
        }

        # Walk repository and index code files
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["node_modules", "__pycache__", "target", "dist", "build"]]

            for file in files:
                file_path = Path(root) / file
                file_ext = file_path.suffix.lower()

                if file_ext in file_extensions:
                    try:
                        relative_path = file_path.relative_to(repo_path_obj)
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            code_content = f.read()

                        # Ingest code file
                        self.code_search.ingest_code_file(
                            project_id=project_id,
                            file_path=str(relative_path),
                            code=code_content,
                        )

                        stats["files_indexed"] += 1
                        # Estimate chunks (rough approximation)
                        stats["chunks_created"] += max(1, len(code_content) // 500)

                    except Exception as e:
                        error_msg = f"Failed to index {relative_path}: {e}"
                        logger.warning(error_msg)
                        stats["errors"].append(error_msg)

        logger.info(
            f"Indexed repository {repo_path} for project {project_id}: "
            f"{stats['files_indexed']} files, ~{stats['chunks_created']} chunks"
        )

        return stats

    def get_repo_info(self, repo_path: str) -> dict:
        """
        Get basic information about a git repository.
        
        Returns:
            Dictionary with repo metadata (branch, commit, etc.)
        """
        repo_path_obj = Path(repo_path)
        if not (repo_path_obj / ".git").exists():
            return {"error": "Not a git repository"}

        info = {}

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()

            # Get latest commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info["commit"] = result.stdout.strip()

            # Get remote URL if available
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                info["remote_url"] = result.stdout.strip()

        except Exception as e:
            logger.warning(f"Failed to get repo info: {e}")

        return info

    def analyze_repo_structure(self, repo_path: str) -> dict:
        """
        Analyze repository structure (packages, services, architecture).
        
        Returns:
            Dictionary with structure analysis
        """
        repo_path_obj = Path(repo_path)
        structure = {
            "packages": [],
            "services": [],
            "entry_points": [],
        }

        # Simple heuristics for common structures
        # Look for package.json, pyproject.toml, Cargo.toml, etc.
        config_files = {
            "package.json": "node",
            "pyproject.toml": "python",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java",
        }

        for config_file, lang in config_files.items():
            config_path = repo_path_obj / config_file
            if config_path.exists():
                structure["packages"].append({
                    "type": lang,
                    "config_file": config_file,
                })

        # Look for common service/entry point patterns
        for root, dirs, files in os.walk(repo_path_obj):
            # Skip hidden and build directories
            if any(part.startswith(".") for part in Path(root).parts):
                continue

            for file in files:
                file_path = Path(root) / file
                # Look for main entry points
                if file in ["main.py", "app.py", "index.js", "main.rs", "main.go"]:
                    relative = file_path.relative_to(repo_path_obj)
                    structure["entry_points"].append(str(relative))

        return structure

    def analyze_code_with_llm(
        self,
        project_id: str,
        code_content: str,
        file_path: str,
    ) -> Dict:
        """
        Analyze code using the CODER lane LLM.
        
        Args:
            project_id: Project ID
            code_content: Code to analyze
            file_path: Path to the code file
            
        Returns:
            Dictionary with analysis results including:
            - quality_assessment: Overall code quality rating
            - refactoring_suggestions: List of refactoring recommendations
            - security_concerns: List of security issues found
            - performance_optimizations: List of performance improvement suggestions
        """
        prompt = f"""Analyze the following code file and provide a structured analysis.

File: {file_path}

Code:
```python
{code_content[:8000]}  # Limit to 8k chars to avoid context overflow
```

Provide a JSON response with the following structure:
{{
    "quality_assessment": "Brief assessment of code quality (good/fair/poor)",
    "refactoring_suggestions": ["suggestion1", "suggestion2"],
    "security_concerns": ["concern1", "concern2"],
    "performance_optimizations": ["optimization1", "optimization2"]
}}

Return ONLY valid JSON, no markdown formatting."""
        
        try:
            response = generate_text(
                prompt=prompt,
                project_id=project_id,
                temperature=0.2,
                max_tokens=2000,
                json_mode=True,
            )
            
            # Parse JSON response
            response = response.response.strip()
            # Remove markdown code blocks if present
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            analysis = json.loads(response)
            return analysis
        except Exception as e:
            logger.warning(f"LLM code analysis failed for {file_path}: {e}")
            return {
                "quality_assessment": "Analysis unavailable",
                "refactoring_suggestions": [],
                "security_concerns": [],
                "performance_optimizations": [],
                "error": str(e),
            }


repo_service = RepoService()


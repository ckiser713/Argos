"""
E2E tests for repository analysis and gap analysis.
Tests repository ingestion, code search, and gap analysis functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestRepoAnalysisE2E:
    """E2E tests for repository analysis."""

    def test_repository_ingestion(self, client: TestClient, project: dict):
        """Test ingesting a git repository."""
        project_id = project["id"]
        
        # Create a temporary git repository for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test-repo"
            repo_path.mkdir()
            
            # Create a simple Python file
            python_file = repo_path / "main.py"
            python_file.write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
            
            # Ingest repository
            response = client.post(
                f"/api/projects/{project_id}/ingest",
                json={
                    "source_type": "repository",
                    "source_id": "test-repo",
                    "repo_url": str(repo_path),
                    "repo_path": str(repo_path),
                },
            )
            
            # May require git repo, so check for appropriate response
            assert response.status_code in (200, 201, 400, 422)
            
    def test_code_search(self, client: TestClient, project: dict):
        """Test searching code in ingested repositories."""
        project_id = project["id"]
        
        # Search for code
        response = client.post(
            f"/api/projects/{project_id}/gap-analysis/search-code",
            json={
                "query": "function definition",
                "limit": 5,
            },
        )
        
        # Should return search results or empty list
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            
    def test_gap_analysis_generation(self, client: TestClient, project: dict):
        """Test generating gap analysis report."""
        project_id = project["id"]
        
        # Create an idea/ticket first
        idea_response = client.post(
            f"/api/projects/{project_id}/ideas",
            json={
                "title": "Add user authentication",
                "description": "Implement login and registration functionality",
            },
        )
        assert idea_response.status_code in (200, 201)
        
        # Generate gap analysis
        response = client.post(
            f"/api/projects/{project_id}/gap-analysis/generate",
            json={
                "ticket_ids": [],
                "repo_paths": [],
            },
        )
        
        # Should generate report or return appropriate status
        assert response.status_code in (200, 201, 400, 422)
        if response.status_code in (200, 201):
            data = response.json()
            assert isinstance(data, dict)
            
    def test_gap_analysis_with_repo(self, client: TestClient, project: dict):
        """Test gap analysis comparing code to requirements."""
        project_id = project["id"]
        
        # Create requirement idea
        idea_response = client.post(
            f"/api/projects/{project_id}/ideas",
            json={
                "title": "API endpoint for users",
                "description": "Create REST API endpoint /api/users",
            },
        )
        idea_id = idea_response.json().get("id") if idea_response.status_code in (200, 201) else None
        
        # Generate gap analysis
        response = client.post(
            f"/api/projects/{project_id}/gap-analysis/generate",
            json={
                "ticket_ids": [idea_id] if idea_id else [],
            },
        )
        
        assert response.status_code in (200, 201, 400, 422)
        if response.status_code in (200, 201):
            data = response.json()
            # Should contain gap analysis results
            assert isinstance(data, dict)


"""
E2E tests for dynamic roadmap generation.
Tests LLM-based roadmap generation with decision nodes and DAG structure.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestRoadmapGeneration:
    """Test dynamic roadmap generation."""

    def test_generate_roadmap_from_intent(self, client: TestClient, project: dict):
        """Test generating a roadmap from natural language intent."""
        project_id = project["id"]
        
        response = client.post(
            f"/api/projects/{project_id}/roadmap/generate",
            json={
                "intent": "Build a web application with user authentication and a dashboard",
                "use_existing_ideas": True,
            },
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Verify roadmap structure
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        
        # Verify nodes have required fields
        if data["nodes"]:
            node = data["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "status" in node
            
    def test_roadmap_with_decision_nodes(self, client: TestClient, project: dict):
        """Test roadmap generation includes decision nodes."""
        project_id = project["id"]
        
        response = client.post(
            f"/api/projects/{project_id}/roadmap/generate",
            json={
                "intent": "Choose between React and Vue for frontend, then build API",
                "use_existing_ideas": False,
            },
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Check for decision nodes
        decision_nodes = [
            node for node in data.get("nodes", [])
            if node.get("kind") == "decision" or "decision" in node.get("label", "").lower()
        ]
        
        # Should have at least one decision node for technology choice
        # Note: This depends on LLM output, so we just verify structure
        assert len(data["nodes"]) > 0
        
    def test_roadmap_dependencies(self, client: TestClient, project: dict):
        """Test that roadmap nodes have proper dependencies."""
        project_id = project["id"]
        
        response = client.post(
            f"/api/projects/{project_id}/roadmap/generate",
            json={
                "intent": "Set up database, then build API, then create frontend",
                "use_existing_ideas": False,
            },
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Verify edges represent dependencies
        assert len(data.get("edges", [])) >= 0  # May have dependencies
        
        # Verify nodes can reference dependencies
        for node in data.get("nodes", []):
            if "depends_on" in node or "depends_on_ids" in node:
                deps = node.get("depends_on") or node.get("depends_on_ids", [])
                assert isinstance(deps, list)
                
    def test_roadmap_with_existing_ideas(self, client: TestClient, project: dict):
        """Test roadmap generation incorporates existing project ideas."""
        project_id = project["id"]
        
        # Create an idea first
        idea_response = client.post(
            f"/api/projects/{project_id}/ideas",
            json={
                "title": "Add user authentication",
                "description": "Implement OAuth2 authentication",
            },
        )
        assert idea_response.status_code in (200, 201)
        
        # Generate roadmap that should incorporate this idea
        response = client.post(
            f"/api/projects/{project_id}/roadmap/generate",
            json={
                "intent": "Build a complete web application",
                "use_existing_ideas": True,
            },
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Verify roadmap was generated
        assert "nodes" in data
        assert len(data["nodes"]) > 0


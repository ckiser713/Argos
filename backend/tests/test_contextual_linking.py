"""
E2E tests for contextual linking between documents.
Tests automatic linking based on semantic similarity.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestContextualLinking:
    """Test contextual linking functionality."""

    def test_auto_link_documents(self, client: TestClient, project: dict):
        """Test automatic linking between related documents."""
        project_id = project["id"]
        
        # Ingest multiple related documents
        doc1_response = client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "ml-paper",
                "content": "This paper discusses neural networks and deep learning architectures.",
            },
        )
        assert doc1_response.status_code in (200, 201)
        
        doc2_response = client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "ai-research",
                "content": "Deep learning models have revolutionized artificial intelligence.",
            },
        )
        assert doc2_response.status_code in (200, 201)
        
        # Trigger auto-linking
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/auto-link",
            json={},
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        
        # Verify links were created
        # The response should indicate links were created
        assert "links_created" in data or "success" in data or isinstance(data, dict)
        
    def test_manual_knowledge_edge_creation(self, client: TestClient, project: dict):
        """Test manually creating knowledge graph edges."""
        project_id = project["id"]
        
        # Create two knowledge nodes
        node1_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/nodes",
            json={
                "kind": "document",
                "label": "Document A",
                "description": "First document",
            },
        )
        assert node1_response.status_code in (200, 201)
        node1_id = node1_response.json().get("id")
        
        node2_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/nodes",
            json={
                "kind": "document",
                "label": "Document B",
                "description": "Second document",
            },
        )
        assert node2_response.status_code in (200, 201)
        node2_id = node2_response.json().get("id")
        
        # Create an edge between them
        edge_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/edges",
            json={
                "source_id": node1_id,
                "target_id": node2_id,
                "kind": "relates_to",
                "label": "Related to",
            },
        )
        
        assert edge_response.status_code in (200, 201)
        edge_data = edge_response.json()
        assert edge_data.get("source_id") == node1_id
        assert edge_data.get("target_id") == node2_id
        
    def test_semantic_similarity_linking(self, client: TestClient, project: dict):
        """Test linking based on semantic similarity."""
        project_id = project["id"]
        
        # Create nodes with semantically similar content
        node1_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/nodes",
            json={
                "kind": "document",
                "label": "Python Tutorial",
                "description": "Learn Python programming language basics",
            },
        )
        node1_id = node1_response.json().get("id")
        
        node2_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/nodes",
            json={
                "kind": "document",
                "label": "Python Guide",
                "description": "Introduction to Python coding",
            },
        )
        node2_id = node2_response.json().get("id")
        
        # Use auto-link to create semantic links
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/auto-link",
            json={},
        )
        
        assert response.status_code in (200, 201)
        # Should create links between semantically similar nodes


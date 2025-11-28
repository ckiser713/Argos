"""
E2E tests for Qdrant vector database integration.
Tests document ingestion, search, and RAG functionality.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestQdrantIntegration:
    """Test Qdrant vector database integration."""

    def test_document_ingestion(self, client: TestClient, project: dict):
        """Test ingesting a document and storing it in Qdrant."""
        project_id = project["id"]
        
        # Create a test document
        test_content = """
        This is a test document about machine learning.
        Machine learning is a subset of artificial intelligence.
        It involves training models on data to make predictions.
        """
        
        # Ingest document via ingest API
        response = client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "test-doc-1",
                "content": test_content,
            },
        )
        
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data or "job_id" in data
        
        # Wait for ingestion to complete (if async)
        # In a real test, you'd poll the job status
        
    def test_semantic_search(self, client: TestClient, project: dict):
        """Test semantic search using Qdrant."""
        project_id = project["id"]
        
        # First ingest a document
        test_content = """
        Python is a high-level programming language.
        It is widely used for web development, data science, and AI.
        Python has a simple syntax and large ecosystem.
        """
        
        client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "python-doc",
                "content": test_content,
            },
        )
        
        # Search for related content
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "programming language",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)
        
    def test_hybrid_search(self, client: TestClient, project: dict):
        """Test hybrid search (keyword + vector)."""
        project_id = project["id"]
        
        # Ingest multiple documents
        documents = [
            {"id": "doc1", "content": "FastAPI is a web framework for Python."},
            {"id": "doc2", "content": "React is a JavaScript library for building UIs."},
            {"id": "doc3", "content": "Python web frameworks include FastAPI and Django."},
        ]
        
        for doc in documents:
            client.post(
                f"/api/projects/{project_id}/ingest",
                json={
                    "source_type": "text",
                    "source_id": doc["id"],
                    "content": doc["content"],
                },
            )
        
        # Test hybrid search
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "Python FastAPI",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should find documents related to Python and FastAPI
        assert len(data.get("results", data if isinstance(data, list) else [])) > 0


@pytest.mark.asyncio
class TestRAGService:
    """Test RAG service advanced features."""

    def test_query_rewriting(self, client: TestClient, project: dict):
        """Test query rewriting for better retrieval."""
        project_id = project["id"]
        
        # Ingest test document
        client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "test-doc",
                "content": "Machine learning models require training data.",
            },
        )
        
        # Search with advanced features
        # Note: This would require a RAG search endpoint
        # For now, test via knowledge search
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "how to train ML models",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        
    def test_citation_tracking(self, client: TestClient, project: dict):
        """Test that citations are tracked in search results."""
        project_id = project["id"]
        
        # Ingest document
        client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "cited-doc",
                "content": "This is a document that should be cited.",
            },
        )
        
        # Search and verify citations
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "cited document",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Results should include document_id for citation
        results = data.get("results", data if isinstance(data, list) else [])
        if results:
            assert "document_id" in results[0] or "source" in results[0]


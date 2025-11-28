"""
E2E tests for advanced RAG features.
Tests query rewriting, multi-hop reasoning, and citation tracking.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestAdvancedRAG:
    """Test advanced RAG features."""

    def test_query_rewriting(self, client: TestClient, project: dict):
        """Test query rewriting for better retrieval."""
        project_id = project["id"]
        
        # Ingest test documents
        documents = [
            "Machine learning requires training data and algorithms.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing analyzes text data.",
        ]
        
        for i, doc in enumerate(documents):
            client.post(
                f"/api/projects/{project_id}/ingest",
                json={
                    "source_type": "text",
                    "source_id": f"doc-{i}",
                    "content": doc,
                },
            )
        
        # Test search with query that should be rewritten
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "how do I train ML models?",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return results even with rewritten query
        
    @patch("app.services.rag_service.generate_text")
    def test_multi_hop_reasoning(self, mock_llm, client: TestClient, project: dict):
        """Test multi-hop reasoning for complex queries."""
        project_id = project["id"]
        
        # Mock LLM responses for multi-hop
        mock_llm.side_effect = [
            "refined query about neural networks",
            "more specific query about deep learning architectures",
        ]
        
        # This would be tested via RAG service directly
        from app.services.rag_service import rag_service
        
        results, reasoning_chain = rag_service.multi_hop_search(
            project_id=project_id,
            query="machine learning",
            max_hops=2,
            limit_per_hop=3,
        )
        
        assert isinstance(results, list)
        assert isinstance(reasoning_chain, list)
        assert len(reasoning_chain) >= 1  # At least original query
        
    def test_citation_tracking(self, client: TestClient, project: dict):
        """Test that citations are properly tracked."""
        project_id = project["id"]
        
        # Ingest document with known content
        doc_id = "citation-test-doc"
        client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": doc_id,
                "content": "This is a test document for citation tracking.",
            },
        )
        
        # Search and verify citations
        response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "citation tracking",
                "max_results": 5,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Results should include document identifiers for citations
        results = data.get("results", data if isinstance(data, list) else [])
        if results:
            result = results[0]
            assert "document_id" in result or "source" in result
            
    def test_query_history(self, client: TestClient, project: dict):
        """Test query history tracking."""
        project_id = project["id"]
        
        # Perform multiple searches
        queries = [
            "machine learning",
            "deep learning",
            "neural networks",
        ]
        
        for query in queries:
            client.post(
                f"/api/projects/{project_id}/knowledge-graph/search",
                json={
                    "query": query,
                    "max_results": 3,
                },
            )
        
        # Query history should be tracked (tested via service)
        from app.services.rag_service import rag_service
        
        history = rag_service.get_query_history(project_id, limit=10)
        assert len(history) > 0
        assert all(isinstance(q, rag_service.RAGQuery) for q in history)
        
    def test_query_refinement(self, client: TestClient, project: dict):
        """Test query refinement based on previous results."""
        project_id = project["id"]
        
        # Ingest documents
        client.post(
            f"/api/projects/{project_id}/ingest",
            json={
                "source_type": "text",
                "source_id": "refine-doc",
                "content": "Python is a programming language used for web development.",
            },
        )
        
        # Initial search
        initial_response = client.post(
            f"/api/projects/{project_id}/knowledge-graph/search",
            json={
                "query": "programming",
                "max_results": 3,
            },
        )
        
        assert initial_response.status_code == 200
        initial_results = initial_response.json().get("results", [])
        
        # Refinement would be tested via service
        from app.services.rag_service import rag_service
        
        if initial_results:
            refined = rag_service.refine_query(
                project_id=project_id,
                original_query="programming",
                previous_results=initial_results,
            )
            assert isinstance(refined, str)
            assert len(refined) > 0


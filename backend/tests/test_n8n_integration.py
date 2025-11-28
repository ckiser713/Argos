"""
E2E tests for n8n workflow integration.
Tests workflow triggering, templates, and error handling.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.mark.asyncio
class TestN8nIntegration:
    """Test n8n workflow integration."""

    def test_list_n8n_workflows(self, client: TestClient):
        """Test listing available n8n workflows."""
        response = client.get("/api/n8n/workflows")
        
        # Should return 200 even if n8n is not running (empty list)
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            
    def test_get_n8n_workflow_templates(self, client: TestClient):
        """Test getting workflow templates."""
        response = client.get("/api/n8n/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify template structure
        if data:
            template = data[0]
            assert "id" in template
            assert "name" in template
            assert "description" in template
            assert "webhook_path" in template
            assert "input_schema" in template
            
    @patch("app.tools.n8n.trigger_n8n_workflow_with_retry")
    async def test_trigger_n8n_workflow_success(self, mock_trigger, client: TestClient):
        """Test successfully triggering an n8n workflow."""
        mock_trigger.return_value = {
            "success": True,
            "workflow_id": "test-workflow",
            "status_code": 200,
            "data": {"result": "success"},
            "attempt": 1,
        }
        
        # This would be called via agent tool, but we can test the tool directly
        from app.tools.n8n import trigger_n8n_workflow
        
        result = await trigger_n8n_workflow("test-workflow", {"key": "value"})
        
        assert "success" in result.lower() or "✅" in result
        mock_trigger.assert_called_once()
        
    @patch("app.tools.n8n.trigger_n8n_workflow_with_retry")
    async def test_trigger_n8n_workflow_retry(self, mock_trigger, client: TestClient):
        """Test n8n workflow retry logic on failure."""
        from app.tools.n8n import N8nWorkflowError
        
        # Simulate retries
        mock_trigger.side_effect = N8nWorkflowError("Workflow failed")
        
        from app.tools.n8n import trigger_n8n_workflow
        
        result = await trigger_n8n_workflow("test-workflow", {"key": "value"})
        
        assert "❌" in result or "failed" in result.lower()
        
    def test_n8n_workflow_executions(self, client: TestClient):
        """Test getting workflow executions."""
        # First need a workflow ID
        workflows_response = client.get("/api/n8n/workflows")
        
        if workflows_response.status_code == 200:
            workflows = workflows_response.json()
            if workflows:
                workflow_id = workflows[0].get("id")
                
                response = client.get(
                    f"/api/n8n/workflows/{workflow_id}/executions",
                    params={"limit": 10},
                )
                
                # May return 404 if workflow doesn't exist or 200 with executions
                assert response.status_code in (200, 404)
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, list)


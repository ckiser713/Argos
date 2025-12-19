"""
n8n workflow management service.

Provides functionality to list, manage, and trigger n8n workflows,
as well as create workflow templates for common automation tasks.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from app.config import get_settings

logger = logging.getLogger("argos.n8n")


class N8nService:
    """Service for managing n8n workflows and templates."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.n8n_base_url
        self.api_key = self.settings.n8n_api_key

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for n8n API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all available n8n workflows.
        
        Returns:
            List of workflow metadata dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/workflows"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                workflows = resp.json()
                return workflows.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list n8n workflows: {e}")
            return []

    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow details by ID.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            Workflow metadata dictionary or None if not found
        """
        try:
            url = f"{self.base_url}/api/v1/workflows/{workflow_id}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._get_headers())
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get n8n workflow {workflow_id}: {e}")
            return None

    async def get_workflow_executions(
        self, workflow_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent workflow executions.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            limit: Maximum number of executions to return
            
        Returns:
            List of execution metadata dictionaries
        """
        try:
            url = f"{self.base_url}/api/v1/executions"
            params = {"limit": limit}
            if workflow_id:
                params["workflowId"] = workflow_id

            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._get_headers(), params=params)
                resp.raise_for_status()
                executions = resp.json()
                return executions.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get n8n executions: {e}")
            return []

    def get_workflow_templates(self) -> List[Dict[str, Any]]:
        """
        Get predefined workflow templates for common tasks.
        
        Returns:
            List of workflow template definitions
        """
        return [
            {
                "id": "git-commit",
                "name": "Git Commit & Push",
                "description": "Commits changes and pushes to a git repository",
                "webhook_path": "webhook/git-commit",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Commit message"},
                        "branch": {"type": "string", "description": "Target branch", "default": "main"},
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of files to commit",
                        },
                        "repo_path": {"type": "string", "description": "Repository path"},
                    },
                    "required": ["message", "repo_path"],
                },
            },
            {
                "id": "slack-notification",
                "name": "Slack Notification",
                "description": "Sends a notification to a Slack channel",
                "webhook_path": "webhook/slack-notify",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Slack channel"},
                        "message": {"type": "string", "description": "Message text"},
                        "username": {"type": "string", "description": "Bot username"},
                    },
                    "required": ["channel", "message"],
                },
            },
            {
                "id": "email-notification",
                "name": "Email Notification",
                "description": "Sends an email notification",
                "webhook_path": "webhook/email-notify",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "id": "github-issue",
                "name": "Create GitHub Issue",
                "description": "Creates an issue in a GitHub repository",
                "webhook_path": "webhook/github-issue",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "Repository (owner/repo)"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body"},
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Issue labels",
                        },
                    },
                    "required": ["repo", "title"],
                },
            },
            {
                "id": "deploy-app",
                "name": "Deploy Application",
                "description": "Triggers application deployment",
                "webhook_path": "webhook/deploy",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "environment": {
                            "type": "string",
                            "description": "Deployment environment",
                            "enum": ["staging", "production"],
                        },
                        "version": {"type": "string", "description": "Version to deploy"},
                        "app_name": {"type": "string", "description": "Application name"},
                    },
                    "required": ["environment", "app_name"],
                },
            },
        ]


# Singleton instance
n8n_service = N8nService()


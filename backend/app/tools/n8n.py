"""
n8n workflow integration tool for Cortex agents.

Provides enhanced workflow triggering with retry logic, error handling,
and response parsing for better integration with LangGraph agents.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx
from app.config import get_settings

try:
    from langchain.tools import tool
except Exception:
    # Fallback decorator if langchain.tools is unavailable or incompatible
    def tool(fn=None, **kwargs):
        def decorator(f):
            return f

        if fn:
            return decorator(fn)
        return decorator

logger = logging.getLogger("cortex.n8n")


class N8nWorkflowError(Exception):
    """Custom exception for n8n workflow errors."""
    pass


async def trigger_n8n_workflow_with_retry(
    workflow_id: str,
    payload: Dict[str, Any],
    base_url: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: int = 300,
) -> Dict[str, Any]:
    """
    Triggers an n8n workflow with retry logic and enhanced error handling.
    
    Args:
        workflow_id: The workflow ID or webhook path
        payload: JSON payload to send to the workflow
        base_url: n8n base URL (defaults to config)
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        timeout: Request timeout in seconds
        
    Returns:
        Dict containing workflow execution result
        
    Raises:
        N8nWorkflowError: If workflow execution fails after all retries
    """
    settings = get_settings()
    base_url = base_url or settings.n8n_base_url
    max_retries = max_retries or settings.n8n_max_retries
    retry_delay = retry_delay or settings.n8n_retry_delay
    timeout = timeout or settings.n8n_webhook_timeout
    
    # Construct webhook URL
    # Support both webhook/{id} and direct webhook paths
    if workflow_id.startswith("webhook/"):
        url = f"{base_url}/{workflow_id}"
    elif "/" in workflow_id:
        # Assume it's a full webhook path
        url = f"{base_url}/{workflow_id}"
    else:
        url = f"{base_url}/webhook/{workflow_id}"
    
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(
                    f"Triggering n8n workflow {workflow_id} (attempt {attempt}/{max_retries})"
                )
                
                # Add headers if API key is configured
                headers = {}
                if settings.n8n_api_key:
                    headers["X-N8N-API-KEY"] = settings.n8n_api_key
                
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                
                # Try to parse response as JSON
                try:
                    result_data = resp.json()
                except (json.JSONDecodeError, ValueError):
                    # If not JSON, return text response
                    result_data = {"status": "success", "response": resp.text}
                
                logger.info(
                    f"n8n workflow {workflow_id} completed successfully (status: {resp.status_code})"
                )
                
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "status_code": resp.status_code,
                    "data": result_data,
                    "attempt": attempt,
                }
                
        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(
                f"n8n workflow {workflow_id} timed out (attempt {attempt}/{max_retries})"
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)  # Exponential backoff
                continue
                
        except httpx.HTTPStatusError as e:
            last_error = e
            # Don't retry on 4xx errors (client errors)
            if 400 <= e.response.status_code < 500:
                logger.error(
                    f"n8n workflow {workflow_id} failed with client error: {e.response.status_code}"
                )
                raise N8nWorkflowError(
                    f"Workflow {workflow_id} failed with status {e.response.status_code}: {e.response.text}"
                ) from e
            
            # Retry on 5xx errors (server errors)
            logger.warning(
                f"n8n workflow {workflow_id} failed with server error: {e.response.status_code} (attempt {attempt}/{max_retries})"
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
                continue
                
        except httpx.RequestError as e:
            last_error = e
            logger.warning(
                f"n8n workflow {workflow_id} request failed (attempt {attempt}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
                continue
                
        except Exception as e:
            last_error = e
            logger.error(
                f"Unexpected error triggering n8n workflow {workflow_id} (attempt {attempt}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * attempt)
                continue
    
    # All retries exhausted
    error_msg = f"Workflow {workflow_id} failed after {max_retries} attempts"
    if last_error:
        error_msg += f": {str(last_error)}"
    
    logger.error(error_msg)
    raise N8nWorkflowError(error_msg) from last_error


@tool
async def trigger_n8n_workflow(workflow_id: str, payload: dict) -> str:
    """
    Triggers an external automation workflow in n8n.
    
    This tool allows agents to trigger n8n workflows for automation tasks such as:
    - Git commits and pushes
    - Sending notifications (email, Slack, Discord)
    - Creating tickets in issue trackers
    - Deploying applications
    - Running CI/CD pipelines
    
    Args:
        workflow_id: The n8n workflow ID or webhook path (e.g., "abc123" or "webhook/git-commit")
        payload: JSON payload to send to the workflow. Should match the workflow's expected input format.
        
    Returns:
        A formatted string describing the workflow execution result.
        
    Example:
        trigger_n8n_workflow("git-commit", {
            "message": "Add new feature",
            "branch": "main",
            "files": ["src/main.py"]
        })
    """
    try:
        result = await trigger_n8n_workflow_with_retry(workflow_id, payload)
        
        # Format response for LLM consumption
        if result["success"]:
            data = result.get("data", {})
            if isinstance(data, dict):
                # Extract meaningful information from response
                response_summary = json.dumps(data, indent=2)
            else:
                response_summary = str(data)
            
            return (
                f"✅ Workflow '{workflow_id}' executed successfully.\n"
                f"Status: {result['status_code']}\n"
                f"Response:\n{response_summary}"
            )
        else:
            return f"⚠️ Workflow '{workflow_id}' completed with warnings. Status: {result.get('status_code', 'unknown')}"
            
    except N8nWorkflowError as e:
        return f"❌ Failed to trigger workflow '{workflow_id}': {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error in trigger_n8n_workflow tool")
        return f"❌ Unexpected error triggering workflow '{workflow_id}': {str(e)}"

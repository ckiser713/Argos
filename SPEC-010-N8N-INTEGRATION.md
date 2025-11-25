# SPEC-010: n8n Webhook Integration

## Context
The architecture diagram shows n8n handling "side-effects" (e.g., "Scrape Tech News", "Git Commit"). Cortex needs a standard way to trigger these.

## Requirements
- **Trigger:** `AgentRun` can output a specific tool call: `trigger_workflow`.
- **Protocol:** HTTP POST to local n8n webhook URL.

## Implementation Guide

### 1. Tool Definition (`backend/app/tools/n8n.py`)
```python
import httpx
from langchain.tools import tool

@tool
async def trigger_n8n_workflow(workflow_id: str, payload: dict):
    """Triggers an external automation workflow in n8n."""
    url = f"http://localhost:5678/webhook/{workflow_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        return f"Workflow {workflow_id} triggered. Status: {resp.status_code}"
```

### 2. Add to LangGraph
Register trigger_n8n_workflow in project_manager_graph.py so the Agent can decide to "Email the report" or "Scrape a URL" by delegating to n8n.
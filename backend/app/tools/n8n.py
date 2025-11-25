import httpx
try:
    from langchain.tools import tool
except ImportError:
    # Fallback for langchain version compatibility
    from langchain_core.tools import tool


@tool
async def trigger_n8n_workflow(workflow_id: str, payload: dict):
    """Triggers an external automation workflow in n8n."""
    url = f"http://localhost:5678/webhook/{workflow_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        return f"Workflow {workflow_id} triggered. Status: {resp.status_code}"

import httpx
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


@tool
async def trigger_n8n_workflow(workflow_id: str, payload: dict):
    """Triggers an external automation workflow in n8n."""
    url = f"http://localhost:5678/webhook/{workflow_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload)
        return f"Workflow {workflow_id} triggered. Status: {resp.status_code}"

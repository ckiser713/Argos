from __future__ import annotations


from typing import Any, Dict


from app.domain.mode import ProjectExecutionSettings
from app.repos import mode_repo




def run_project_manager_graph(
    project_id: str,
    input_payload: Dict[str, Any],
) -> Dict[str, Any]:
    settings: ProjectExecutionSettings = mode_repo.get_project_settings(project_id)


    # Example: pass execution settings into the LangGraph runtime config.
    runtime_config = {
        "mode": settings.mode,
        "max_parallel_tools": settings.max_parallel_tools,
        "validation_passes": settings.validation_passes,
    }


    # TODO: integrate with your actual LangGraph execution call, e.g.:
    # return langgraph_runner.run(graph_name="project_manager", payload=input_payload, config=runtime_config)
    raise NotImplementedError

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.services.llm_service import generate_text
from app.repos.mode_repo import get_project_settings
from app.domain.mode import ProjectExecutionSettings

logger = logging.getLogger(__name__)


def generate_roadmap_from_intent(project_id: str, intent: str) -> dict:
    prompt = f"Generate a roadmap for: {intent}"
    # Force JSON mode in LLM (if supported) or parse text
    response_json = generate_text(prompt, json_mode=True) 
    data = json.loads(response_json)
    
    # Auto-Layout Logic
    # Assign X,Y based on 'phase_index'
    for node in data['nodes']:
        phase = node.get('phase_index', 0)
        node['y'] = phase * 150
        node['x'] = 250 + (node.get('sibling_index', 0) * 200)
        
    # Save to DB (using Repo from SPEC-001)
    return data


def run_roadmap_planner(
    project_id: str,
    input_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Runs the roadmap planner, which is likely a LangGraph agent.
    Behavior is adjusted based on project execution settings (normal vs. paranoid).
    """
    settings: ProjectExecutionSettings = get_project_settings(project_id)

    logger.info(
        "roadmap_service.run_roadmap_planner.start",
        extra={
            "project_id": project_id,
            "mode": settings.mode,
            "validation_passes": settings.validation_passes,
            "max_parallel_tools": settings.max_parallel_tools,
        },
    )

    if settings.mode == "normal":
        # Normal mode: faster, single-pass planning.
        return _run_single_planner_instance(
            project_id=project_id,
            payload=input_payload,
            planner_seed=0,
            max_parallel_tools=settings.max_parallel_tools,
        )

    # Paranoid mode: redundant planners + consensus checker.
    result_a = _run_single_planner_instance(
        project_id=project_id,
        payload=input_payload,
        planner_seed=0,
        max_parallel_tools=settings.max_parallel_tools,
    )
    result_b = _run_single_planner_instance(
        project_id=project_id,
        payload=input_payload,
        planner_seed=1,
        max_parallel_tools=settings.max_parallel_tools,
    )

    consensus = _run_planner_consensus_checker(
        project_id=project_id,
        base_payload=input_payload,
        result_a=result_a,
        result_b=result_b,
        validation_passes=settings.validation_passes,
    )

    return consensus


def _run_single_planner_instance(
    project_id: str,
    payload: Dict[str, Any],
    *,
    planner_seed: int,
    max_parallel_tools: int,
) -> Dict[str, Any]:
    """Invoke the underlying LangGraph / planner.

    `planner_seed` can be wired into your graph's random / sampling controls
    to encourage diversity between redundant runs.
    """
    # TODO: integrate with your existing LangGraph runner; this is a structural stub.
    logger.warning(
        "Using dummy single planner instance for project %s (seed: %s)",
        project_id,
        planner_seed,
    )
    return {"plan": f"Plan for {project_id} (seed {planner_seed})", "status": "stubbed"}


def _run_planner_consensus_checker(
    project_id: str,
    base_payload: Dict[str, Any],
    result_a: Dict[str, Any],
    result_b: Dict[str, Any],
    *,
    validation_passes: int,
) -> Dict[str, Any]:
    """Run a consensus / checker step, likely via a smaller LLM or rules.

    In paranoid mode, this is where you can:
      - detect divergent plans,
      - merge or highlight conflicts,
      - enforce additional constraints (e.g., budget, timeline).
    """
    logger.info(
        "roadmap_service.consensus_checker.start",
        extra={
            "project_id": project_id,
            "validation_passes": validation_passes,
        },
    )

    # TODO: call into a checker agent or LLM summarizer.
    logger.warning(
        "Using dummy planner consensus checker for project %s (validation passes: %s)",
        project_id,
        validation_passes,
    )
    return {
        "consensus_plan": "Consensus plan based on multiple runs",
        "status": "stubbed_consensus",
        "original_a": result_a,
        "original_b": result_b,
    }


def run_roadmap_planner(
    project_id: str,
    input_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Runs the roadmap planner, which is likely a LangGraph agent.
    Behavior is adjusted based on project execution settings (normal vs. paranoid).
    """
    settings: ProjectExecutionSettings = get_project_settings(project_id)

    logger.info(
        "roadmap_service.run_roadmap_planner.start",
        extra={
            "project_id": project_id,
            "mode": settings.mode,
            "validation_passes": settings.validation_passes,
            "max_parallel_tools": settings.max_parallel_tools,
        },
    )

    if settings.mode == "normal":
        # Normal mode: faster, single-pass planning.
        return _run_single_planner_instance(
            project_id=project_id,
            payload=input_payload,
            planner_seed=0,
            max_parallel_tools=settings.max_parallel_tools,
        )

    # Paranoid mode: redundant planners + consensus checker.
    result_a = _run_single_planner_instance(
        project_id=project_id,
        payload=input_payload,
        planner_seed=0,
        max_parallel_tools=settings.max_parallel_tools,
    )
    result_b = _run_single_planner_instance(
        project_id=project_id,
        payload=input_payload,
        planner_seed=1,
        max_parallel_tools=settings.max_parallel_tools,
    )

    consensus = _run_planner_consensus_checker(
        project_id=project_id,
        base_payload=input_payload,
        result_a=result_a,
        result_b=result_b,
        validation_passes=settings.validation_passes,
    )

    return consensus


def _run_single_planner_instance(
    project_id: str,
    payload: Dict[str, Any],
    *,
    planner_seed: int,
    max_parallel_tools: int,
) -> Dict[str, Any]:
    """Invoke the underlying LangGraph / planner.

    `planner_seed` can be wired into your graph's random / sampling controls
    to encourage diversity between redundant runs.
    """
    # TODO: integrate with your existing LangGraph runner; this is a structural stub.
    logger.warning(
        "Using dummy single planner instance for project %s (seed: %s)",
        project_id,
        planner_seed,
    )
    return {"plan": f"Plan for {project_id} (seed {planner_seed})", "status": "stubbed"}


def _run_planner_consensus_checker(
    project_id: str,
    base_payload: Dict[str, Any],
    result_a: Dict[str, Any],
    result_b: Dict[str, Any],
    *,
    validation_passes: int,
) -> Dict[str, Any]:
    """Run a consensus / checker step, likely via a smaller LLM or rules.

    In paranoid mode, this is where you can:
      - detect divergent plans,
      - merge or highlight conflicts,
      - enforce additional constraints (e.g., budget, timeline).
    """
    logger.info(
        "roadmap_service.consensus_checker.start",
        extra={
            "project_id": project_id,
            "validation_passes": validation_passes,
        },
    )

    # TODO: call into a checker agent or LLM summarizer.
    logger.warning(
        "Using dummy planner consensus checker for project %s (validation passes: %s)",
        project_id,
        validation_passes,
    )
    return {
        "consensus_plan": "Consensus plan based on multiple runs",
        "status": "stubbed_consensus",
        "original_a": result_a,
        "original_b": result_b,
    }

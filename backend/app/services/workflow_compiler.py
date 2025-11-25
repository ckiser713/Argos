from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.domain.models import WorkflowGraph, WorkflowNode

logger = logging.getLogger("cortex.workflow")


class WorkflowState(TypedDict):
    """State for workflow execution."""

    run_id: str
    project_id: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    messages: list
    current_node: Optional[str]


class WorkflowGraphCompiler:
    """Compiles WorkflowGraph to LangGraph StateGraph."""

    def compile(self, workflow_graph: WorkflowGraph) -> StateGraph:
        """Compile workflow graph to LangGraph StateGraph."""
        graph = StateGraph(WorkflowState)

        # Add nodes
        for node in workflow_graph.nodes:
            graph.add_node(node.id, self._create_node_function(node))

        # Add edges
        entry_node = None
        for edge in workflow_graph.edges:
            if edge.source == "__start__":
                entry_node = edge.target
            elif edge.target == "__end__":
                graph.add_edge(edge.source, END)
            else:
                graph.add_edge(edge.source, edge.target)

        # Set entry point
        if entry_node:
            graph.set_entry_point(entry_node)
        elif workflow_graph.nodes:
            # Default to first node if no explicit entry point
            graph.set_entry_point(workflow_graph.nodes[0].id)

        return graph.compile()

    def _create_node_function(self, node: WorkflowNode):
        """Create executable function for workflow node."""

        async def node_function(state: WorkflowState):
            # This is a placeholder - actual execution logic will be handled
            # by the WorkflowService during execution
            logger.info(f"Executing node {node.id} for run {state['run_id']}")

            # Return state with node output
            return {"output": {**state.get("output", {}), node.id: f"Node {node.id} executed"}, "current_node": node.id}

        return node_function

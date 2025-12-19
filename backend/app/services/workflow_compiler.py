import logging
from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.domain.models import WorkflowGraph, WorkflowNode, WorkflowNodeStatus
# Import `tool_executor` lazily inside _execute_node_logic to avoid circular import at module import time
from app.domain.model_lanes import ModelLane
from app.services.llm_service import generate_text

logger = logging.getLogger("argos.workflow")


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

    def __init__(self, workflow_service=None):
        """
        Initialize compiler with optional workflow service for node state tracking.
        
        Args:
            workflow_service: WorkflowService instance for updating node states during execution
        """
        self.workflow_service = workflow_service

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
            run_id = state.get("run_id")
            project_id = state.get("project_id")
            
            logger.info(
                "workflow_compiler.node_execution.start",
                extra={"run_id": run_id, "node_id": node.id, "node_label": node.label},
            )

            # Update node state to RUNNING if workflow service is available
            if self.workflow_service and run_id:
                try:
                    self.workflow_service.set_node_state(
                        run_id=run_id,
                        node_id=node.id,
                        status=WorkflowNodeStatus.RUNNING,
                        progress=0.0,
                        started=True,
                    )
                except Exception as e:
                    logger.warning(
                        "workflow_compiler.node_state_update_failed",
                        extra={"run_id": run_id, "node_id": node.id, "error": str(e)},
                    )

            try:
                # Execute node logic
                node_output = self._execute_node_logic(node, state)
                
                # Update node state to COMPLETED if workflow service is available
                if self.workflow_service and run_id:
                    try:
                        message_text = ""
                        if isinstance(node_output, dict):
                            message_text = node_output.get("output") or node_output.get("result") or ""
                        else:
                            message_text = str(node_output)
                        self.workflow_service.set_node_state(
                            run_id=run_id,
                            node_id=node.id,
                            status=WorkflowNodeStatus.COMPLETED,
                            progress=1.0,
                            completed=True,
                            messages=[m for m in [f"Node {node.label} executed successfully", message_text] if m],
                        )
                    except Exception as e:
                        logger.warning(
                            "workflow_compiler.node_state_update_failed",
                            extra={"run_id": run_id, "node_id": node.id, "error": str(e)},
                        )

                logger.info(
                    "workflow_compiler.node_execution.completed",
                    extra={"run_id": run_id, "node_id": node.id},
                )

                # Return updated state with node output
                return {
                    "output": {**state.get("output", {}), node.id: node_output},
                    "current_node": node.id,
                }

            except Exception as e:
                logger.exception(
                    "workflow_compiler.node_execution.failed",
                    extra={"run_id": run_id, "node_id": node.id, "error": str(e)},
                )

                # Update node state to FAILED if workflow service is available
                if self.workflow_service and run_id:
                    try:
                        self.workflow_service.set_node_state(
                            run_id=run_id,
                            node_id=node.id,
                            status=WorkflowNodeStatus.FAILED,
                            progress=0.0,
                            completed=True,
                            error=str(e),
                        )
                    except Exception as update_error:
                        logger.error(
                            "workflow_compiler.node_state_update_failed",
                            extra={"run_id": run_id, "node_id": node.id, "error": str(update_error)},
                        )

                # Re-raise to allow LangGraph to handle the error
                raise

        return node_function

    def _execute_node_logic(self, node: WorkflowNode, state: WorkflowState) -> Any:
        """
        Execute the actual logic for a workflow node.
        
        This implementation supports:
        - LLM nodes: Generate text using LLM service
        - Tool nodes: Execute external tools/APIs
        - Condition nodes: Evaluate conditions and branch
        
        Args:
            node: The workflow node to execute
            state: Current workflow state
            
        Returns:
            Output from node execution
        """
        input_data = state.get("input", {})
        node_type = getattr(node, "type", "noop")
        config = getattr(node, "config", {})

        if node_type == "llm":
            prompt_template = config.get("prompt", node.label)
            prompt = prompt_template.format(**input_data)
            
            project_id = state.get("project_id")

            llm_response = generate_text(
                prompt=prompt,
                project_id=project_id,
                lane=ModelLane.ORCHESTRATOR,
            )

            return {
                "node_id": node.id,
                "type": node_type,
                "prompt": prompt,
                "output": llm_response.response,
                "reasoning": llm_response.reasoning_trace,
            }

        if node_type == "tool":
            tool_name = config.get("tool_name", node.label)
            params = config.get("params", {})
            
            args = {**params, **input_data}
            if 'project_id' not in args:
                args['project_id'] = state.get('project_id')

            call = {"name": tool_name, "args": args}
            # Lazily import tool_executor to avoid circular import during module load
            from app.graphs.project_manager_graph import tool_executor
            result = tool_executor.invoke(call)
            
            return {
                "node_id": node.id,
                "type": node_type,
                "tool": tool_name,
                "params": args,
                "output": result,
            }

        if node_type == "condition":
            path = config.get("path")
            expected = config.get("equals")
            actual = self._extract_path(state, path) if path else None
            return {
                "node_id": node.id,
                "type": node_type,
                "path": path,
                "actual": actual,
                "equals": expected,
                "result": actual == expected,
            }

        # Default noop: echo label and input
        return {
            "node_id": node.id,
            "type": node_type,
            "node_label": node.label,
            "output": f"Executed node: {node.label}",
            "processed_input": input_data,
        }

    def _extract_path(self, state: WorkflowState, path: str | None) -> Any:
        """Read dotted path from workflow state or return None."""
        if not path:
            return None
        cursor: Any = state
        for part in path.split("."):
            if isinstance(cursor, dict) and part in cursor:
                cursor = cursor[part]
            else:
                return None
        return cursor

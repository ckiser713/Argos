Goal: Implement the LangGraph state machine that drives agent behavior.

Markdown

# SPEC-005: LangGraph Orchestration Engine

## Context
`project_manager_graph.py` is empty. We need a state machine that can loop, call tools, and maintain memory of the current goal.

## Requirements
- **State Schema:** Must track `messages` list, `current_step`, and `generated_artifacts`.
- **Tools:** Bind `RagService.search` and `RoadmapService.create_nodes` as tools.
- **Graph Structure:** `Start` -> `Agent` -> `ToolNode` -> `Agent` -> `End`.

## Implementation Guide (`backend/app/graphs/project_manager_graph.py`)

```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.services.llm_service import get_llm_client # From SPEC-003
from app.services.rag_service import rag_service    # From SPEC-002

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    project_id: str

def project_manager_agent(state: AgentState):
    """The Brain: Decides whether to call a tool or finish."""
    messages = state['messages']
    llm = get_llm_client() # Configured with tools
    response = llm.invoke(messages)
    return {"messages": [response]}

def tool_execution_node(state: AgentState):
    """The Hands: Executes the tool requested by the LLM."""
    last_message = state['messages'][-1]
    tool_call = last_message.tool_calls[0]
    
    if tool_call['name'] == 'search_knowledge':
        result = rag_service.search(tool_call['args']['query'])
        return {"messages": [AIMessage(content=str(result))]}
    
    # ... handle other tools like save_roadmap ...

# Graph Construction
workflow = StateGraph(AgentState)
workflow.add_node("agent", project_manager_agent)
workflow.add_node("tools", tool_execution_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    lambda x: "tools" if x['messages'][-1].tool_calls else END
)
workflow.add_edge("tools", "agent")

app = workflow.compile()
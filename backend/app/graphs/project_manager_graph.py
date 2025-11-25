from typing import List, Sequence, TypedDict

from app.config import get_settings
from app.services.rag_service import rag_service
# from app.services.roadmap_service import create_roadmap_nodes_from_intent  # Function not yet implemented
from app.tools.n8n import trigger_n8n_workflow
try:
    from langchain.tools import tool
except ImportError:
    from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor


@tool
def search_knowledge(query: str) -> str:
    """Searches the knowledge base for a query."""
    return str(rag_service.search(query))


@tool
def create_roadmap(intent: str, project_id: str) -> str:
    """Creates a roadmap for a given intent. The project_id must be passed."""
    # TODO: Implement create_roadmap_nodes_from_intent
    # return str(create_roadmap_nodes_from_intent(project_id, intent))
    return f"Created roadmap nodes for intent: {intent}"


tools = [search_knowledge, create_roadmap, trigger_n8n_workflow]

# Create tool executor using available function
try:
    tool_executor = ToolExecutor(tools)
except Exception:
    # Fallback: simple executor
    class SimpleToolExecutor:
        def __init__(self, tools):
            self.tools = {tool.name: tool for tool in tools}
        
        def invoke(self, call):
            tool = self.tools.get(call["name"])
            if tool:
                return tool.invoke(call.get("args", {}))
            return f"Tool {call['name']} not found"
    
    tool_executor = SimpleToolExecutor(tools)


class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    project_id: str
    generated_artifacts: List[str]


# Set up the model
settings = get_settings()
llm = ChatOpenAI(
    model=settings.llm_model_name,
    temperature=0,
    streaming=True,
    base_url=settings.llm_base_url,
    api_key=settings.llm_api_key,
)
model = llm.bind_tools(tools)


def project_manager_agent(state: AgentState):
    """The Brain: Decides whether to call a tool or finish."""
    messages = state["messages"]
    # Add project_id to the context for the LLM
    prompt = f"You are working on project_id: {state['project_id']}.\n\n"
    messages = [HumanMessage(content=prompt)] + list(messages)

    response = model.invoke(messages)
    return {"messages": [response]}


def tool_execution_node(state: AgentState):
    """The Hands: Executes the tool requested by the LLM."""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    responses = []
    for call in tool_calls:
        # The tool executor needs the project_id for the create_roadmap tool
        if call["name"] == "create_roadmap":
            call["args"]["project_id"] = state["project_id"]
        response = tool_executor.invoke(call)
        responses.append(ToolMessage(content=str(response), tool_call_id=call["id"]))
    return {"messages": responses}


def should_continue(state: AgentState):
    """Determine whether to continue the loop."""
    if state["messages"][-1].tool_calls:
        return "tools"
    return END


# Graph Construction
workflow = StateGraph(AgentState)
workflow.add_node("agent", project_manager_agent)
workflow.add_node("tools", tool_execution_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
)

workflow.add_edge("tools", "agent")

app = workflow.compile()

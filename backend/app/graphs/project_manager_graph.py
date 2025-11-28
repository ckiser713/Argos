from typing import List, Sequence, TypedDict

from app.config import get_settings
from app.services.rag_service import rag_service
from app.services.roadmap_service import create_roadmap_nodes_from_intent
from app.tools.n8n import trigger_n8n_workflow
try:
    from langchain.tools import tool
except Exception:
    # Provide a no-op fallback tool decorator if the langchain.tools integration fails
    def tool(fn=None, **kwargs):
        def decorator(f):
            return f

        if fn:
            return decorator(fn)
        return decorator
from langchain.messages import AnyMessage as BaseMessage, HumanMessage, ToolMessage
from langchain.chat_models.base import init_chat_model
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_node import ToolNode


@tool
def search_knowledge(query: str, project_id: str = "") -> str:
    """
    Searches the knowledge base for a query.
    
    Args:
        query: The search query
        project_id: The project ID (will be injected automatically)
    """
    if not project_id:
        # Fallback: try to get from context if available
        return "Error: project_id is required for knowledge search"
    
    try:
        # Use advanced RAG features
        result = rag_service.search(
            project_id=project_id,
            query=query,
            limit=5,
            use_advanced=True,
        )
        
        # Format results with citations
        if result.get("results"):
            formatted = "Search Results:\n\n"
            for i, r in enumerate(result["results"], 1):
                formatted += f"{i}. [Score: {r['score']:.3f}] {r['content'][:200]}...\n"
                if r.get("document_id"):
                    formatted += f"   Source: {r['document_id']} (chunk {r.get('chunk_index', '?')})\n"
                formatted += "\n"
            
            if result.get("citations"):
                formatted += "\nCitations:\n"
                for i, cit in enumerate(result["citations"], 1):
                    formatted += f"{i}. {cit['document_id']} (chunk {cit['chunk_index']})\n"
            
            return formatted
        else:
            return "No results found for your query."
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"


@tool
def create_roadmap(intent: str, project_id: str) -> str:
    """Creates a roadmap for a given intent. The project_id must be passed."""
    try:
        nodes = create_roadmap_nodes_from_intent(project_id, intent)
        node_labels = [node.label for node in nodes]
        return f"Created {len(nodes)} roadmap nodes: {', '.join(node_labels)}"
    except Exception as e:
        return f"Error creating roadmap: {str(e)}"


tools = [search_knowledge, create_roadmap, trigger_n8n_workflow]

# Create tool executor using available function
try:
    tool_executor = ToolNode(tools)
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


# Set up the model using ORCHESTRATOR lane configuration
settings = get_settings()
try:
    # Use default model for the agent
    model_name = settings.llm_model_name
    base_url = settings.llm_base_url
    
    llm = init_chat_model(
        model=model_name,
        model_provider="openai",
        api_key=settings.llm_api_key,
        base_url=base_url,
        temperature=0,
        streaming=True,
    )
    model = llm.bind_tools(tools)
except Exception:
    # Fallback: Use a very small dummy model to keep the server running
    class DummyModel:
        def __init__(self, *args, **kwargs):
            self.name = "dummy"

        def invoke(self, messages):
            from langchain.messages import AIMessage

            return AIMessage(content="I am a dummy model")

        def bind_tools(self, tools):
            return self

    model = DummyModel()


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
        # Inject project_id for tools that need it
        if call["name"] == "create_roadmap":
            call["args"]["project_id"] = state["project_id"]
        elif call["name"] == "search_knowledge":
            # Inject project_id for knowledge search
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

app = workflow.compile(checkpointer=MemorySaver(), interrupt_before=["tools"])

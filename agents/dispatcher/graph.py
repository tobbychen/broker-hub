"""LangGraph state graph for the Dispatcher agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from .nodes import monitor_handler, research_router, approval_router
from ..config import get_llm_config


def _get_llm():
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    return ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )


def create_dispatcher_graph():
    """Build the dispatcher state graph."""
    graph = StateGraph(dict)

    llm = _get_llm()

    graph.add_node("monitor_handler", lambda s: monitor_handler(s, llm))
    graph.add_node("research_router", lambda s: research_router(s, llm))
    graph.add_node("approval_router", lambda s: approval_router(s, llm))

    graph.set_entry_point("monitor_handler")
    graph.add_edge("monitor_handler", "research_router")
    graph.add_edge("research_router", "approval_router")
    graph.add_edge("approval_router", END)

    return graph.compile()


_dispatcher_graph = None

def get_dispatcher():
    global _dispatcher_graph
    if _dispatcher_graph is None:
        _dispatcher_graph = create_dispatcher_graph()
    return _dispatcher_graph

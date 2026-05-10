"""LangGraph state graph for the Dispatcher agent — orchestrator version."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dataclasses import dataclass, field
from typing import Literal

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from .nodes import (
    monitor_handler,
    research_router,
    approval_router,
    portfolio_tracker_node,
    risk_manager_node,
    trade_executor_node,
    log_and_discard_node,
)
from ..config import get_llm_config


@dataclass
class DispatcherState:
    """Typed state for the dispatcher orchestrator."""
    alerts: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    pending_approval: list = field(default_factory=list)
    research_results: dict = field(default_factory=dict)
    risk_checks: dict = field(default_factory=dict)
    draft_orders: dict = field(default_factory=dict)
    routed_to: str = "END"


def _get_llm():
    cfg = get_llm_config()
    primary = cfg.get("primary", {})
    return ChatOpenAI(
        api_key=primary.get("api_key", ""),
        model=primary.get("model", "auto"),
        base_url=primary.get("base_url", "https://api.minimax.chat/v1"),
        temperature=0.3,
    )


def _make_node(fn, llm):
    """Wrap an async node function with the LLM injected."""
    async def node(state):
        return await fn(state, llm)
    return node


def _route_after_monitor(state: DispatcherState) -> str:
    """After monitor_handler: if decisions were created, go to portfolio_tracker."""
    if state.get("decisions"):
        return "portfolio_tracker"
    return "END"


def _route_after_portfolio(state: DispatcherState) -> str:
    """After portfolio_tracker: always go to research_router."""
    return "research_router"


def _route_after_research(state: DispatcherState) -> str:
    """Route based on research confidence."""
    decisions = state.get("decisions", [])
    if not decisions:
        return "END"
    last = decisions[-1]
    confidence = last.get("confidence", 0.0)
    confidence_threshold = 0.6
    if confidence < confidence_threshold:
        return "log_and_discard"
    return "risk_manager"


def _route_after_risk(state: DispatcherState) -> str:
    """Route based on risk check result."""
    risk_checks = state.get("risk_checks", {})
    passed = risk_checks.get("passed", False)
    if not passed:
        return "log_and_discard"
    return "approval_router"


def _route_after_approval(state: DispatcherState) -> str:
    """Route based on human decision status stored in state."""
    decisions = state.get("decisions", [])
    if not decisions:
        return "END"
    last = decisions[-1]
    status = last.get("status", "pending")
    if status == "approved":
        return "trade_executor"
    return "log_and_discard"


def create_dispatcher_graph() -> StateGraph:
    """Build the dispatcher state graph as an orchestrator."""
    graph = StateGraph(DispatcherState)
    llm = _get_llm()

    # Core nodes
    graph.add_node("monitor_handler", _make_node(monitor_handler, llm))
    graph.add_node("portfolio_tracker", _make_node(portfolio_tracker_node, llm))
    graph.add_node("research_router", _make_node(research_router, llm))
    graph.add_node("risk_manager", _make_node(risk_manager_node, llm))
    graph.add_node("approval_router", _make_node(approval_router, llm))
    graph.add_node("trade_executor", _make_node(trade_executor_node, llm))
    graph.add_node("log_and_discard", log_and_discard_node)

    # Entry point
    graph.set_entry_point("monitor_handler")

    # Conditional flow after monitor_handler
    graph.add_conditional_edges(
        "monitor_handler",
        _route_after_monitor,
        {
            "portfolio_tracker": "portfolio_tracker",
            "END": END,
        },
    )

    # portfolio_tracker always goes to research_router
    graph.add_edge("portfolio_tracker", "research_router")

    # Conditional flow after research_router
    graph.add_conditional_edges(
        "research_router",
        _route_after_research,
        {
            "risk_manager": "risk_manager",
            "log_and_discard": "log_and_discard",
            "END": END,
        },
    )

    # risk_manager conditional
    graph.add_conditional_edges(
        "risk_manager",
        _route_after_risk,
        {
            "approval_router": "approval_router",
            "log_and_discard": "log_and_discard",
        },
    )

    # approval_router conditional
    graph.add_conditional_edges(
        "approval_router",
        _route_after_approval,
        {
            "trade_executor": "trade_executor",
            "log_and_discard": "log_and_discard",
        },
    )

    # trade_executor ends
    graph.add_edge("trade_executor", END)

    # log_and_discard ends
    graph.add_edge("log_and_discard", END)

    return graph.compile()


_dispatcher_graph = None


def get_dispatcher():
    global _dispatcher_graph
    if _dispatcher_graph is None:
        _dispatcher_graph = create_dispatcher_graph()
    return _dispatcher_graph

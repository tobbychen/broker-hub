"""Tests for dispatcher agent."""
import pytest
from agents.dispatcher.graph import create_dispatcher_graph


def test_dispatcher_graph_creation():
    """Test that dispatcher graph can be created."""
    graph = create_dispatcher_graph()
    assert graph is not None
    # LangGraph compiled graphs have invoke/ainvoke methods
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "ainvoke")
    assert callable(graph.ainvoke)

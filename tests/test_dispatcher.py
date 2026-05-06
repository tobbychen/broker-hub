"""Tests for dispatcher agent."""
import pytest
from agents.dispatcher.graph import create_dispatcher_graph


def test_dispatcher_graph_creation():
    graph = create_dispatcher_graph()
    assert graph is not None
    assert callable(graph)

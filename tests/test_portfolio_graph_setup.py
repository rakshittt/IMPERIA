"""Graph wiring tests for portfolio research flow."""

from unittest.mock import MagicMock

import pytest

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup


def _passthrough(state):
    return state


@pytest.mark.unit
def test_graph_setup_has_portfolio_flow_without_trader():
    tool_nodes = {
        "market": _passthrough,
        "social": _passthrough,
        "news": _passthrough,
        "fundamentals": _passthrough,
    }
    setup = GraphSetup(
        quick_thinking_llm=MagicMock(),
        deep_thinking_llm=MagicMock(),
        tool_nodes=tool_nodes,
        conditional_logic=ConditionalLogic(),
    )
    workflow = setup.setup_graph(["market"])
    node_names = set(workflow.nodes)
    assert "Trader" not in node_names
    assert "Risk Analyst" in node_names
    assert "Portfolio Manager" in node_names
    assert "Aggressive Analyst" not in node_names
    assert "Conservative Analyst" not in node_names
    assert "Neutral Analyst" not in node_names

    edges = {(edge[0], edge[1]) for edge in workflow.edges}
    assert ("Research Manager", "Risk Analyst") in edges
    assert ("Risk Analyst", "Portfolio Manager") in edges

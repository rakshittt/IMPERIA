"""Tests for portfolio feedback memory and graph API compatibility."""

import functools
from unittest.mock import MagicMock

import pytest

from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.agents.utils.agent_utils import normalize_portfolio
from tradingagents.dataflows.utils import portfolio_key
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.trading_graph import TradingAgentsGraph


PORTFOLIO = [
    {"ticker": "AAPL", "weight": 0.6, "shares": 10, "cost_basis": 150},
    {"ticker": "MSFT", "weight": 0.4, "shares": 5, "cost_basis": 300},
]
PROFILE = {
    "risk_tolerance": "moderate",
    "time_horizon": "3-5 years",
    "goals": "long-term growth",
    "constraints": "avoid high volatility",
}
FEEDBACK = (
    "**Overall Assessment**: Quality portfolio with concentration risk.\n\n"
    "**Disclaimer**: This is educational research, not personalized financial advice "
    "or an instruction to trade."
)


def make_log(tmp_path):
    return TradingMemoryLog({"memory_log_path": str(tmp_path / "portfolio_memory.md")})


@pytest.mark.unit
class TestPortfolioMemoryLog:
    def test_store_feedback_creates_completed_entry(self, tmp_path):
        log = make_log(tmp_path)
        key = portfolio_key(PORTFOLIO)
        log.store_feedback(key, "2026-01-10", "AAPL/MSFT portfolio", FEEDBACK)
        entries = log.load_entries()
        assert len(entries) == 1
        assert entries[0]["portfolio_key"] == key
        assert entries[0]["pending"] is False
        assert entries[0]["feedback"] == FEEDBACK
        assert log.get_pending_entries() == []

    def test_store_feedback_is_idempotent(self, tmp_path):
        log = make_log(tmp_path)
        key = portfolio_key(PORTFOLIO)
        log.store_feedback(key, "2026-01-10", "Portfolio", FEEDBACK)
        log.store_feedback(key, "2026-01-10", "Portfolio", FEEDBACK)
        assert len(log.load_entries()) == 1

    def test_past_context_prefers_same_portfolio(self, tmp_path):
        log = make_log(tmp_path)
        key = portfolio_key(PORTFOLIO)
        other = portfolio_key([{"ticker": "SPY", "weight": 1.0}])
        log.store_feedback(other, "2026-01-09", "SPY portfolio", "Other feedback.")
        log.store_feedback(key, "2026-01-10", "AAPL/MSFT portfolio", FEEDBACK)
        context = log.get_past_context(key)
        assert "Past feedback for this portfolio" in context
        assert key in context
        assert "Recent portfolio research lessons" in context
        assert other in context

    def test_outcome_updates_are_noops(self, tmp_path):
        log = make_log(tmp_path)
        key = portfolio_key(PORTFOLIO)
        log.store_feedback(key, "2026-01-10", "Portfolio", FEEDBACK)
        log.update_with_outcome(key, "2026-01-10", 0.1, 0.05, 5, "ignored")
        log.batch_update_with_outcomes([{"portfolio_key": key}])
        entries = log.load_entries()
        assert entries[0]["pending"] is False
        assert "ignored" not in entries[0]["feedback"]


@pytest.mark.unit
class TestPropagatorPortfolioState:
    def test_initial_state_contains_portfolio_and_profile(self):
        state = Propagator().create_initial_state(
            PORTFOLIO,
            "2026-01-10",
            user_profile=PROFILE,
            past_context="prior feedback",
        )
        assert state["analysis_date"] == "2026-01-10"
        assert state["user_portfolio"][0]["ticker"] == "AAPL"
        assert state["user_profile"]["risk_tolerance"] == "moderate"
        assert state["portfolio_key"] == portfolio_key(state["user_portfolio"])
        assert state["past_context"] == "prior feedback"
        assert "research_debate_state" in state
        assert "final_portfolio_feedback" in state
        assert "risk_report" in state


@pytest.mark.unit
class TestTradingAgentsGraphPortfolioApi:
    def test_run_graph_stores_feedback_and_returns_it(self, tmp_path):
        fake_state = Propagator().create_initial_state(PORTFOLIO, "2026-01-10", PROFILE)
        fake_state.update(
            {
                "market_report": "Market.",
                "sentiment_report": "Sentiment.",
                "news_report": "News.",
                "fundamentals_report": "Fundamentals.",
                "bullish_research": "Bullish.",
                "bearish_research": "Bearish.",
                "research_synthesis": "Synthesis.",
                "risk_report": "Risk.",
                "final_portfolio_feedback": FEEDBACK,
            }
        )

        mock_graph = MagicMock()
        mock_graph.memory_log = TradingMemoryLog(
            {"memory_log_path": str(tmp_path / "portfolio_memory.md")}
        )
        mock_graph.log_states_dict = {}
        mock_graph.debug = False
        mock_graph.config = {"results_dir": str(tmp_path), "checkpoint_enabled": False}
        mock_graph.graph.invoke.return_value = fake_state
        mock_graph.propagator.create_initial_state.return_value = fake_state
        mock_graph.propagator.get_graph_args.return_value = {}
        mock_graph._run_graph = functools.partial(TradingAgentsGraph._run_graph, mock_graph)
        mock_graph._log_state = functools.partial(TradingAgentsGraph._log_state, mock_graph)

        final_state, feedback = TradingAgentsGraph._run_graph(
            mock_graph, PORTFOLIO, "2026-01-10", PROFILE
        )
        assert final_state == fake_state
        assert feedback == FEEDBACK
        entries = mock_graph.memory_log.load_entries()
        assert len(entries) == 1
        assert entries[0]["portfolio_key"] == portfolio_key(PORTFOLIO)

    def test_propagate_wraps_single_holding(self):
        graph = MagicMock()
        graph.analyze_portfolio.return_value = ("state", "feedback")
        result = TradingAgentsGraph.propagate(graph, "NVDA", "2026-01-10")
        assert result == ("state", "feedback")
        graph.analyze_portfolio.assert_called_once_with(
            [{"ticker": "NVDA", "weight": 1.0}],
            "2026-01-10",
            user_profile=None,
        )

    def test_analyze_portfolio_is_primary_api(self):
        graph = MagicMock()
        graph.config = {"checkpoint_enabled": False}
        graph._checkpointer_ctx = None
        graph._run_graph.return_value = ("state", "feedback")
        result = TradingAgentsGraph.analyze_portfolio(
            graph, PORTFOLIO, "2026-01-10", user_profile=PROFILE
        )
        assert result == ("state", "feedback")
        assert graph.portfolio_key == portfolio_key(normalize_portfolio(PORTFOLIO))
        args, kwargs = graph._run_graph.call_args
        assert args[1] == "2026-01-10"
        assert kwargs == {}

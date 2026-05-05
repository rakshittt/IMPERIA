from typing import Any, Dict, List, Optional

from tradingagents.agents.utils.agent_states import ResearchDebateState
from tradingagents.agents.utils.agent_utils import (
    build_portfolio_context,
    normalize_portfolio,
    normalize_user_profile,
)
from tradingagents.dataflows.utils import portfolio_key


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self,
        portfolio: list[dict],
        analysis_date: str,
        user_profile: dict | None = None,
        past_context: str = "",
    ) -> Dict[str, Any]:
        """Create the initial portfolio state for the agent graph."""
        normalized_portfolio = normalize_portfolio(portfolio)
        normalized_profile = normalize_user_profile(user_profile)
        context = build_portfolio_context(normalized_portfolio, normalized_profile)
        key = portfolio_key(normalized_portfolio)
        return {
            "messages": [("human", context)],
            "user_portfolio": normalized_portfolio,
            "user_profile": normalized_profile,
            "portfolio_context": context,
            "portfolio_key": key,
            "analysis_date": str(analysis_date),
            "past_context": past_context,
            "research_debate_state": ResearchDebateState(
                {
                    "bullish_history": "",
                    "bearish_history": "",
                    "history": "",
                    "current_response": "",
                    "judge_decision": "",
                    "count": 0,
                }
            ),
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "macro_report": "",
            "sec_filings_report": {},
            "earnings_report": {},
            "macro_context_report": {},
            "bullish_research": "",
            "bearish_research": "",
            "research_synthesis": "",
            "trader_report": "",
            "risk_report": "",
            "final_portfolio_feedback": "",
        }

    def get_graph_args(self, callbacks: Optional[List] = None) -> Dict[str, Any]:
        """Get arguments for graph invocation."""
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }

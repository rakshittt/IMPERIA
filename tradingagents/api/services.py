"""Backend services shared by API routes."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.persistence.portfolio import persist_research_result

load_dotenv()

RESEARCH_STAGES = [
    "market_report",
    "sentiment_report",
    "news_report",
    "fundamentals_report",
    "macro_report",
    "bullish_research",
    "bearish_research",
    "research_synthesis",
    "trader_report",
    "risk_report",
    "final_portfolio_feedback",
]

research_store: dict[str, dict[str, Any]] = {}
_TRADING_GRAPH = None


def get_analysis_date(value: str | None = None) -> str:
    return value or datetime.now().strftime("%Y-%m-%d")


def get_trading_graph():
    """Lazy-load the deep research graph so fast API imports stay cheap."""

    global _TRADING_GRAPH
    if _TRADING_GRAPH is None:
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = DEFAULT_CONFIG.copy()
        config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", config["deep_think_llm"])
        config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", config["quick_think_llm"])
        debug = os.getenv("TRADINGAGENTS_API_DEBUG", "false").lower() in {"1", "true", "yes"}
        _TRADING_GRAPH = TradingAgentsGraph(debug=debug, config=config)
    return _TRADING_GRAPH


def normalize_research_result(final_state: dict[str, Any], research_id: str | None = None) -> dict[str, Any]:
    rid = research_id or str(uuid.uuid4())[:8]
    result = {"id": rid, "status": "completed"}
    for stage in RESEARCH_STAGES:
        result[stage] = final_state.get(stage, "")
    research_store[rid] = result
    persist_research_result(rid, result, status="completed")
    return result


def run_deep_research(
    portfolio: list[dict[str, Any]],
    analysis_date: str | None = None,
    profile: dict[str, Any] | None = None,
    research_id: str | None = None,
) -> dict[str, Any]:
    graph = get_trading_graph()
    final_state, _feedback = graph.analyze_portfolio(
        portfolio,
        get_analysis_date(analysis_date),
        profile or {},
    )
    return normalize_research_result(final_state, research_id=research_id)

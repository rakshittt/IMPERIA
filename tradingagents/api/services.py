"""Backend services shared by API routes."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.demo_provider import get_demo_research_report, is_demo_mode
from tradingagents.expert_agents.runtime import run_stock_research
from tradingagents.persistence.portfolio import persist_research_result
from tradingagents.workers.background_jobs import emit_research_event

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
    holdings = final_state.get("user_portfolio", []) or []
    ticker = holdings[0].get("ticker") if holdings else None
    result = {
        "id": rid,
        "research_id": rid,
        "status": "completed",
        "ticker": ticker,
        "topic": ticker,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "executive_summary": final_state.get("final_portfolio_feedback", "") or final_state.get("research_synthesis", ""),
        "what_happened_recently": final_state.get("market_report", ""),
        "company_overview": final_state.get("fundamentals_report", ""),
        "market_snapshot": final_state.get("market_report", ""),
        "financial_analysis": final_state.get("fundamentals_report", ""),
        "earnings_analysis": final_state.get("earnings_report", {}),
        "sec_filing_insights": final_state.get("sec_filings_report", {}),
        "news_context": final_state.get("news_report", ""),
        "prediction_market_sentiment": final_state.get("sentiment_report", ""),
        "bull_thesis": final_state.get("bullish_research", ""),
        "bear_thesis": final_state.get("bearish_research", ""),
        "key_risks": final_state.get("risk_report", ""),
        "what_to_watch_next": final_state.get("trader_report", ""),
        "data_quality_warnings": [],
        "citations": [],
        "agent_outputs": {},
        "not_investment_advice": True,
    }
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
    if is_demo_mode() and portfolio:
        ticker = str(portfolio[0].get("ticker", "")).upper()
        demo = get_demo_research_report(ticker)
        if demo:
            rid = research_id or str(uuid.uuid4())[:8]
            result = {"id": rid, "research_id": rid, **demo, "status": "completed", "not_investment_advice": True}
            research_store[rid] = result
            persist_research_result(rid, result, status="completed")
            return result
    graph = get_trading_graph()
    final_state, _feedback = graph.analyze_portfolio(
        portfolio,
        get_analysis_date(analysis_date),
        profile or {},
    )
    return normalize_research_result(final_state, research_id=research_id)


def run_stock_expert_research(
    portfolio: list[dict[str, Any]],
    analysis_date: str | None = None,
    profile: dict[str, Any] | None = None,
    research_id: str | None = None,
) -> dict[str, Any]:
    """Run stock-first expert-agent research without requiring portfolio inputs."""

    profile = profile or {}
    ticker = str(profile.get("ticker") or (portfolio[0].get("ticker") if portfolio else "")).upper()
    if not ticker:
        raise ValueError("stock-first expert research requires a ticker")

    def _emit(event: str, **payload: Any) -> None:
        if research_id:
            emit_research_event(research_id, event, **payload)

    _emit("data_collection_started", warnings=[])
    _emit("synthesis_started", warnings=[])
    result = run_stock_research(
        ticker,
        question=profile.get("question") or f"Deep research report on {ticker}",
        window=profile.get("window"),
        mode="deep",
        research_id=research_id,
        emit_event=_emit,
    )
    _emit("synthesis_completed", warnings=result.get("warnings", [])[:5])
    _emit("audit_started", warnings=[])
    _emit("completed", warnings=result.get("warnings", [])[:5])
    rid = research_id or str(uuid.uuid4())[:8]
    result["id"] = rid
    result["research_id"] = rid
    research_store[rid] = result
    persist_research_result(rid, result, status="completed")
    return result

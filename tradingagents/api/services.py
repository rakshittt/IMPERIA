"""Backend services shared by API routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from tradingagents.providers.demo.provider import get_demo_research_report, is_demo_mode
from tradingagents.core.research.runtime import run_stock_research
from tradingagents.infra.db.portfolio import persist_research_result
from tradingagents.core.research.jobs import emit_research_event

research_store: dict[str, dict[str, Any]] = {}


def _ticker_from_portfolio(portfolio: list[dict[str, Any]]) -> str:
    """Extract the primary ticker from a portfolio list."""
    if not portfolio:
        raise ValueError("research requires at least one ticker")
    return str(portfolio[0].get("ticker", "")).upper()


def run_stock_expert_research(
    portfolio: list[dict[str, Any]],
    analysis_date: str | None = None,
    profile: dict[str, Any] | None = None,
    research_id: str | None = None,
) -> dict[str, Any]:
    """Run stock-first expert-agent research.

    Accepts a portfolio list for backward compatibility with the job runner
    signature; the primary ticker is extracted from the first holding.
    """
    profile = profile or {}
    ticker = str(profile.get("ticker") or _ticker_from_portfolio(portfolio))

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


def run_deep_research(
    portfolio: list[dict[str, Any]],
    analysis_date: str | None = None,
    profile: dict[str, Any] | None = None,
    research_id: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible alias — delegates to the expert-agent runtime.

    The legacy TradingAgentsGraph path has been retired from the API; all
    research now uses the stock-first expert-agent graph which provides
    consistent, source-cited output with graceful degradation.
    """
    if is_demo_mode() and portfolio:
        ticker = str(portfolio[0].get("ticker", "")).upper()
        demo = get_demo_research_report(ticker)
        if demo:
            rid = research_id or str(uuid.uuid4())[:8]
            result = {"id": rid, "research_id": rid, **demo, "status": "completed", "not_investment_advice": True}
            research_store[rid] = result
            persist_research_result(rid, result, status="completed")
            return result
    return run_stock_expert_research(portfolio, analysis_date, profile, research_id)

"""Earnings and guidance specialist agent for deep research context."""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.dataflows.earnings_data import (
    get_earnings_history,
    get_earnings_surprise_stats,
    get_next_earnings,
)
from tradingagents.dataflows.news_aggregator import get_earnings_news

logger = logging.getLogger(__name__)


class EarningsAnalysisReport(BaseModel):
    """Structured earnings quality report."""

    summary: str
    beat_miss_rate: dict[str, Any] = Field(default_factory=dict)
    guidance_flags: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _holding_tickers(state: dict[str, Any]) -> list[str]:
    return [str(item.get("ticker", "")).upper() for item in state.get("user_portfolio", []) if item.get("ticker")]


def create_earnings_analyst(llm):
    """Create an additive specialist node for earnings trajectory analysis."""

    def earnings_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        for ticker in _holding_tickers(state):
            try:
                next_event = get_next_earnings(ticker)
                rows.append(
                    {
                        "ticker": ticker,
                        "history": [item.model_dump() for item in get_earnings_history(ticker, limit=8)],
                        "stats": get_earnings_surprise_stats(ticker).model_dump(),
                        "next": next_event.model_dump() if next_event else None,
                        "news": [item.model_dump() for item in get_earnings_news(ticker)[:5]],
                    }
                )
            except Exception as exc:
                logger.warning("earnings_specialist_failed ticker=%s error=%s", ticker, type(exc).__name__)
                warnings.append(f"{ticker}: earnings data unavailable ({type(exc).__name__}).")
        summary = "\n".join(f"{row['ticker']}: {row['stats'].get('quarters', 0)} quarters of surprise history reviewed." for row in rows)
        report = EarningsAnalysisReport(summary=summary or "No earnings data available.", warnings=warnings)
        if rows:
            prompt = (
                "You are an earnings quality and guidance analyst. Use only this data. Interpret beat/miss "
                "trajectory, average surprise, guidance credibility, and quality risks. Keep it concise.\n"
                f"Portfolio context:\n{state.get('portfolio_context','')}\n\nEarnings data:\n{rows}"
            )
            try:
                response = llm.invoke(prompt)
                if getattr(response, "content", None):
                    report.summary = response.content
            except Exception as exc:
                report.warnings.append(f"DeepSeek earnings synthesis unavailable ({type(exc).__name__}).")
        logger.info("agent_completed agent_name=Earnings Analyst duration_ms=%d data_points_used=%d", int((time.perf_counter() - started) * 1000), len(rows))
        return {"earnings_report": report.model_dump()}

    return earnings_node

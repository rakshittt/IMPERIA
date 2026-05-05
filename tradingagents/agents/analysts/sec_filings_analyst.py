"""SEC filings specialist agent for deep research context."""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.dataflows.sec_edgar import (
    get_13f_related_filings,
    get_form4_insider_trades,
    get_sec_filings,
    get_xbrl_financials,
)

logger = logging.getLogger(__name__)


class SECFilingsReport(BaseModel):
    """Structured SEC filings summary for one portfolio run."""

    summary: str
    key_flags: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _holding_tickers(state: dict[str, Any]) -> list[str]:
    return [str(item.get("ticker", "")).upper() for item in state.get("user_portfolio", []) if item.get("ticker")]


def _fallback_report(rows: list[dict[str, Any]], warnings: list[str]) -> SECFilingsReport:
    parts = []
    citations = []
    for row in rows:
        ticker = row["ticker"]
        filings = row.get("filings", [])
        forms = ", ".join(item.get("filing_type", "") for item in filings[:5]) or "no recent filings"
        parts.append(f"{ticker}: recent SEC filings reviewed ({forms}).")
        citations.extend({"source_type": "sec", "title": item.get("filing_type"), "url": item.get("url")} for item in filings[:3])
    return SECFilingsReport(summary="\n".join(parts) or "No SEC filing data available.", citations=citations, warnings=warnings)


def create_sec_filings_analyst(llm):
    """Create an additive specialist node that summarizes SEC filings."""

    def sec_filings_node(state: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        rows: list[dict[str, Any]] = []
        warnings: list[str] = []
        for ticker in _holding_tickers(state):
            try:
                filings = get_sec_filings(ticker, limit=12)
                rows.append(
                    {
                        "ticker": ticker,
                        "filings": filings,
                        "xbrl": get_xbrl_financials(ticker),
                        "form4": get_form4_insider_trades(ticker, limit=10),
                        "thirteen_f": get_13f_related_filings(ticker, limit=10),
                    }
                )
            except Exception as exc:
                logger.warning("sec_specialist_failed ticker=%s error=%s", ticker, type(exc).__name__)
                warnings.append(f"{ticker}: SEC data unavailable ({type(exc).__name__}).")
        report = _fallback_report(rows, warnings)
        if rows:
            prompt = (
                "You are an SEC filings analyst. Use only this data. Focus on 10-K/10-Q risk flags, "
                "MD&A/accounting changes, goodwill impairment, debt covenant risk, Form 4 insider signals, "
                f"and 13F limitations. Portfolio context:\n{state.get('portfolio_context','')}\n\nSEC data:\n{rows}"
            )
            try:
                response = llm.invoke(prompt)
                if getattr(response, "content", None):
                    report.summary = response.content
            except Exception as exc:
                warnings.append(f"DeepSeek SEC filing synthesis unavailable ({type(exc).__name__}).")
        logger.info("agent_completed agent_name=SEC Filings Analyst duration_ms=%d data_points_used=%d", int((time.perf_counter() - started) * 1000), len(rows))
        return {"sec_filings_report": report.model_dump()}

    return sec_filings_node

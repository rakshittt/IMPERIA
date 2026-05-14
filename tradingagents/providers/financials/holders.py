"""Institutional-holder analysis for IMPERIA research flows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

import tradingagents.providers.demo.provider as demo_provider
from tradingagents.providers.filings.thirteen_f import get_thirteen_f_activity
from tradingagents.utils.validation import normalize_ticker


class InstitutionalHolder(BaseModel):
    holder_name: str
    shares: float | None = None
    value: float | None = None
    pct_held: float | None = None
    as_of_date: str | None = None


class InstitutionalHolderAnalysis(BaseModel):
    ticker: str
    holders: list[InstitutionalHolder] = Field(default_factory=list)
    thirteen_f_summary: dict[str, Any] = Field(default_factory=dict)
    institutional_net_action: str = "none"
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "", "None") else None
    except (TypeError, ValueError):
        return None


def get_institutional_holder_analysis(ticker: str, limit: int = 10) -> InstitutionalHolderAnalysis:
    """Return top institutional holders when yfinance exposes them."""

    symbol = normalize_ticker(ticker)
    if demo_provider.is_demo_mode() and symbol in demo_provider.demo_universe():
        return InstitutionalHolderAnalysis(
            ticker=symbol,
            holders=[
                InstitutionalHolder(holder_name="Demo Index Fund", shares=1_000_000, value=100_000_000, pct_held=0.02, as_of_date=datetime.now(timezone.utc).date().isoformat()),
                InstitutionalHolder(holder_name="Demo Growth Fund", shares=500_000, value=50_000_000, pct_held=0.01, as_of_date=datetime.now(timezone.utc).date().isoformat()),
            ],
            thirteen_f_summary=get_thirteen_f_activity(symbol).model_dump(),
            institutional_net_action="balanced",
            warnings=[demo_provider.DEMO_WARNING, "13F and holder data can be lagged or incomplete."],
            citations=[demo_provider.demo_citation("institutional_holders", f"{symbol} demo institutional holders", ticker=symbol)],
        )
    warnings: list[str] = ["13F and institutional-holder data can be lagged or incomplete."]
    citations: list[dict[str, Any]] = []
    holders: list[InstitutionalHolder] = []
    try:
        import yfinance as yf

        raw = getattr(yf.Ticker(symbol), "institutional_holders", None)
        if raw is not None and not raw.empty:
            for _, row in raw.head(limit).iterrows():
                holders.append(
                    InstitutionalHolder(
                        holder_name=str(row.get("Holder") or row.get("holder") or "Unknown holder"),
                        shares=_float(row.get("Shares") or row.get("shares")),
                        value=_float(row.get("Value") or row.get("value")),
                        pct_held=_float(row.get("% Out") or row.get("pctHeld")),
                        as_of_date=str(row.get("Date Reported") or row.get("dateReported") or "") or None,
                    )
                )
            citations.append({"source_type": "institutional_holders", "provider": "yfinance", "title": f"{symbol} institutional holders", "url": f"https://finance.yahoo.com/quote/{symbol}/holders", "ticker": symbol})
        else:
            warnings.append(f"No yfinance institutional holder table found for {symbol}.")
    except Exception as exc:
        warnings.append(f"Institutional holder data unavailable ({type(exc).__name__}).")
    thirteen_f = get_thirteen_f_activity(symbol, limit=limit)
    warnings.extend(thirteen_f.warnings)
    citations.extend(thirteen_f.citations)
    action = "none" if not holders else "balanced"
    return InstitutionalHolderAnalysis(
        ticker=symbol,
        holders=holders,
        thirteen_f_summary=thirteen_f.model_dump(),
        institutional_net_action=action,
        warnings=warnings,
        citations=citations,
    )

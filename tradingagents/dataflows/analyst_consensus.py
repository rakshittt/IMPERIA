"""Analyst consensus provider for IMPERIA sentiment analysis."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows import demo_provider
from tradingagents.utils.http import safe_get_json
from tradingagents.utils.validation import normalize_ticker

FINNHUB_BASE_URL = os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1")


class AnalystConsensus(BaseModel):
    ticker: str
    buy_count: int | None = None
    hold_count: int | None = None
    sell_count: int | None = None
    strong_buy_count: int | None = None
    strong_sell_count: int | None = None
    mean_target: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    provider: str = "Finnhub"
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def get_analyst_consensus(ticker: str) -> AnalystConsensus:
    """Fetch free-tier analyst consensus data when configured."""

    symbol = normalize_ticker(ticker)
    if demo_provider.is_demo_mode() and symbol in demo_provider.demo_universe():
        index = demo_provider.demo_universe().index(symbol)
        return AnalystConsensus(
            ticker=symbol,
            buy_count=8 + index % 9,
            hold_count=3 + index % 5,
            sell_count=index % 3,
            strong_buy_count=2 + index % 4,
            strong_sell_count=0,
            mean_target=100 + index * 3.5,
            target_high=115 + index * 3.5,
            target_low=80 + index * 2.8,
            provider=demo_provider.DEMO_SOURCE,
            warnings=[demo_provider.DEMO_WARNING, "Analyst consensus is third-party opinion data, not an IMPERIA recommendation."],
            citations=[demo_provider.demo_citation("analyst_consensus", f"{symbol} demo analyst consensus", ticker=symbol)],
        )
    cache = get_default_cache()
    cached = cache.get("analyst_consensus", symbol)
    if cached is not None:
        return AnalystConsensus.model_validate(cached)
    token = os.getenv("FINNHUB_API_KEY")
    if not token:
        return AnalystConsensus(ticker=symbol, warnings=["FINNHUB_API_KEY is not configured; analyst consensus unavailable."])
    warnings: list[str] = []
    rec = safe_get_json(
        f"{FINNHUB_BASE_URL.rstrip('/')}/stock/recommendation",
        params={"symbol": symbol, "token": token},
        source="finnhub_analyst_consensus",
        attempts=3,
    )
    target = safe_get_json(
        f"{FINNHUB_BASE_URL.rstrip('/')}/stock/price-target",
        params={"symbol": symbol, "token": token},
        source="finnhub_price_target",
        attempts=3,
    )
    latest = rec[0] if isinstance(rec, list) and rec else {}
    if not latest:
        warnings.append(f"No Finnhub recommendation trend returned for {symbol}.")
    if not isinstance(target, dict):
        target = {}
        warnings.append(f"No Finnhub price-target data returned for {symbol}.")
    result = AnalystConsensus(
        ticker=symbol,
        buy_count=latest.get("buy"),
        hold_count=latest.get("hold"),
        sell_count=latest.get("sell"),
        strong_buy_count=latest.get("strongBuy"),
        strong_sell_count=latest.get("strongSell"),
        mean_target=target.get("targetMean"),
        target_high=target.get("targetHigh"),
        target_low=target.get("targetLow"),
        warnings=warnings + ["Analyst consensus is third-party opinion data, not an IMPERIA recommendation."],
        citations=[
            {
                "id": f"c_fh_analyst_{symbol.lower()}",
                "source_type": "analyst_consensus",
                "provider": "Finnhub",
                "title": f"{symbol} analyst recommendation trend",
                "url": "https://finnhub.io",
                "ticker": symbol,
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )
    cache.set("analyst_consensus", symbol, result.model_dump(), ttl_seconds=6 * 60 * 60)
    return result

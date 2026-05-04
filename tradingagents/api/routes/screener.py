from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from tradingagents.api.deps import get_fast_engine

router = APIRouter(prefix="/api/screener", tags=["screener"])


class ScreenerRequest(BaseModel):
    query: str | None = None
    max_pe: float | None = None
    min_market_cap: float | None = None
    limit: int = 10


@router.post("")
async def screen(request: ScreenerRequest) -> dict[str, Any]:
    engine = get_fast_engine()
    universe = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD", "NFLX", "JPM", "UNH", "XOM", "LLY"]
    rows = []
    for ticker in universe:
        try:
            quote = engine.get_quote(ticker)
            ratios = engine.get_ratios(ticker).get("metrics", {})
            if request.max_pe is not None and ratios.get("pe") is not None and ratios["pe"] > request.max_pe:
                continue
            if request.min_market_cap is not None and (quote.get("market_cap") or 0) < request.min_market_cap:
                continue
            rows.append({"ticker": ticker, "quote": quote, "metrics": ratios})
        except Exception:
            continue
    return {
        "query": request.query,
        "results": rows[: max(1, min(request.limit, 25))],
        "source": "curated US large-cap universe with free yfinance/computed metrics",
    }

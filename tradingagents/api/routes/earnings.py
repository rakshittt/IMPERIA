from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.api.deps import get_fast_engine

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/calendar")
async def earnings_calendar(symbols: str = Query("AAPL,MSFT,NVDA")):
    engine = get_fast_engine()
    tickers = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    return {"symbols": tickers, "earnings": [engine.get_earnings(ticker) for ticker in tickers[:25]]}

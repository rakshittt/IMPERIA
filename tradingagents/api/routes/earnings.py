from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.dataflows import earnings_data

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


@router.get("/calendar")
async def earnings_calendar(
    start: str | None = Query(None),
    end: str | None = Query(None),
    tickers: str | None = Query(None),
):
    symbols = [item.strip().upper() for item in (tickers or "").split(",") if item.strip()] or None
    return [item.model_dump() for item in earnings_data.get_earnings_calendar(start_date=start, end_date=end, tickers=symbols)]


@router.get("/{ticker}/history")
async def earnings_history(ticker: str, limit: int = Query(8, ge=1, le=32)):
    return [item.model_dump() for item in earnings_data.get_earnings_history(ticker, limit=limit)]


@router.get("/{ticker}/next")
async def next_earnings(ticker: str):
    event = earnings_data.get_next_earnings(ticker)
    return event.model_dump() if event else {"ticker": ticker.upper(), "event": None}


@router.get("/{ticker}/surprise-stats")
async def surprise_stats(ticker: str):
    return earnings_data.get_earnings_surprise_stats(ticker).model_dump()

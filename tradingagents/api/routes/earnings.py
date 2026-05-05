from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from tradingagents.dataflows import earnings_data
from tradingagents.utils.validation import normalize_ticker, validate_iso_date

router = APIRouter(prefix="/api/earnings", tags=["earnings"])


def _ticker(value: str) -> str:
    try:
        return normalize_ticker(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["path", "ticker"], "msg": str(exc), "type": "value_error"}]) from exc


@router.get("/calendar")
async def earnings_calendar(
    start: str | None = Query(None),
    end: str | None = Query(None),
    tickers: str | None = Query(None),
):
    try:
        start = validate_iso_date(start)
        end = validate_iso_date(end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["query"], "msg": str(exc), "type": "value_error"}]) from exc
    symbols = [item.strip().upper() for item in (tickers or "").split(",") if item.strip()] or None
    if symbols:
        symbols = [_ticker(symbol) for symbol in symbols]
    return [item.model_dump() for item in earnings_data.get_earnings_calendar(start_date=start, end_date=end, tickers=symbols)]


@router.get("/{ticker}/history")
async def earnings_history(ticker: str, limit: int = Query(8, ge=1, le=32)):
    ticker = _ticker(ticker)
    return [item.model_dump() for item in earnings_data.get_earnings_history(ticker, limit=limit)]


@router.get("/{ticker}/next")
async def next_earnings(ticker: str):
    ticker = _ticker(ticker)
    event = earnings_data.get_next_earnings(ticker)
    return event.model_dump() if event else {"ticker": ticker.upper(), "event": None}


@router.get("/{ticker}/surprise-stats")
async def surprise_stats(ticker: str):
    ticker = _ticker(ticker)
    return earnings_data.get_earnings_surprise_stats(ticker).model_dump()

from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.api.deps import get_fast_engine
from tradingagents.dataflows import earnings_data, market_data, news_aggregator

router = APIRouter(prefix="/api/stock", tags=["stock"])
compat_router = APIRouter(tags=["compat"])


@router.get("/{ticker}/profile")
async def profile(ticker: str):
    return get_fast_engine().get_profile(ticker)


@router.get("/{ticker}/financials")
async def financials(ticker: str):
    return get_fast_engine().get_financials(ticker)


@router.get("/{ticker}/ratios")
async def ratios(ticker: str):
    return get_fast_engine().get_ratios(ticker)


@router.get("/{ticker}/chart")
async def chart(
    ticker: str,
    period: str = Query("1mo"),
    interval: str = Query("1d"),
):
    frame = market_data.get_ohlcv(ticker, period=period, interval=interval)
    return {"ticker": ticker.upper(), "period": period, "interval": interval, "points": market_data.ohlcv_to_records(frame)}


@router.get("/{ticker}/intraday")
async def intraday(ticker: str, interval: str = Query("5m")):
    frame = market_data.get_intraday(ticker, interval=interval)
    return {"ticker": ticker.upper(), "interval": interval, "points": market_data.ohlcv_to_records(frame)}


@router.get("/{ticker}/news")
async def news(ticker: str, limit: int = Query(10, ge=1, le=50)):
    return {"ticker": ticker.upper(), "articles": [item.model_dump() for item in news_aggregator.get_stock_news(ticker, limit=limit)]}


@router.get("/{ticker}/earnings")
async def earnings(ticker: str):
    return {"ticker": ticker.upper(), "history": [item.model_dump() for item in earnings_data.get_earnings_history(ticker)]}


@router.get("/{ticker}/next-earnings")
async def next_earnings(ticker: str):
    event = earnings_data.get_next_earnings(ticker)
    return event.model_dump() if event else {"ticker": ticker.upper(), "event": None}


@router.get("/{ticker}/holders")
async def holders(ticker: str):
    return get_fast_engine().get_holders(ticker)


@router.get("/{ticker}/filings")
async def filings(
    ticker: str,
    filing_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    return {
        "ticker": ticker.upper(),
        "filings": get_fast_engine().get_filings(ticker, filing_type=filing_type, limit=limit),
    }


@router.get("/{ticker}/insiders")
async def insiders(ticker: str, limit: int = Query(50, ge=1, le=100)):
    return {"ticker": ticker.upper(), "transactions": get_fast_engine().get_insider_trades(ticker, limit=limit)}


@router.get("/{ticker}/ai-summary")
async def ai_summary(ticker: str):
    return get_fast_engine().answer_query(f"Summarize {ticker}")


@compat_router.get("/api/quote/{ticker}")
async def quote_compat(ticker: str):
    quote = market_data.get_quote(ticker).model_dump()
    return {
        "ticker": quote.get("ticker"),
        "name": quote.get("name"),
        "exchange": quote.get("exchange"),
        "price": quote.get("price"),
        "change": quote.get("change"),
        "changePct": quote.get("change_pct"),
        "prevClose": quote.get("previous_close"),
        "open": quote.get("open"),
        "dayHigh": quote.get("day_high"),
        "dayLow": quote.get("day_low"),
        "volume": quote.get("volume"),
        "marketCap": quote.get("market_cap"),
    }

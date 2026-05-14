from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from tradingagents.api.deps import get_fast_engine
from tradingagents.api.responses import standard_response
import tradingagents.providers.financials.earnings as earnings_data
import tradingagents.providers.market.data as market_data
import tradingagents.providers.news.aggregator as news_aggregator
from tradingagents.core.intelligence import stock as stock_intelligence
from tradingagents.core.intelligence.sentiment import get_stock_sentiment
from tradingagents.utils.validation import normalize_ticker

router = APIRouter(prefix="/api/stock", tags=["stock"])
compat_router = APIRouter(tags=["compat"])


def _ticker(value: str) -> str:
    try:
        return normalize_ticker(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["path", "ticker"], "msg": str(exc), "type": "value_error"}]) from exc


def _window(value: str) -> str:
    try:
        return news_aggregator.normalize_news_window(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=[{"loc": ["query", "window"], "msg": str(exc), "type": "value_error"}]) from exc


@router.get("/{ticker}/profile")
async def profile(ticker: str):
    ticker = _ticker(ticker)
    return get_fast_engine().get_profile(ticker)


@router.get("/{ticker}/financials")
async def financials(ticker: str):
    ticker = _ticker(ticker)
    return get_fast_engine().get_financials(ticker)


@router.get("/{ticker}/ratios")
async def ratios(ticker: str):
    ticker = _ticker(ticker)
    return get_fast_engine().get_ratios(ticker)


@router.get("/{ticker}/chart")
async def chart(
    ticker: str,
    period: str = Query("1mo"),
    interval: str = Query("1d"),
):
    ticker = _ticker(ticker)
    frame = market_data.get_ohlcv(ticker, period=period, interval=interval)
    return {"ticker": ticker.upper(), "period": period, "interval": interval, "points": market_data.ohlcv_to_records(frame)}


@router.get("/{ticker}/intraday")
async def intraday(ticker: str, interval: str = Query("5m")):
    ticker = _ticker(ticker)
    frame = market_data.get_intraday(ticker, interval=interval)
    return {"ticker": ticker.upper(), "interval": interval, "points": market_data.ohlcv_to_records(frame)}


def _stock_news(ticker: str, *, limit: int, window: str):
    try:
        return news_aggregator.get_stock_news(ticker, limit=limit, window=window)
    except TypeError:
        return news_aggregator.get_stock_news(ticker, limit=limit)


@router.get("/{ticker}/news")
async def news(
    ticker: str,
    limit: int = Query(10, ge=1, le=50),
    window: str = Query("today"),
):
    ticker = _ticker(ticker)
    normalized_window = _window(window)
    articles = [item.model_dump() for item in _stock_news(ticker, limit=limit, window=normalized_window)]
    return {
        "ticker": ticker.upper(),
        "window": normalized_window,
        "articles": articles,
        "summarized_news": "; ".join(item.get("title", "") for item in articles[:3] if item.get("title")),
        "sentiment_summary": {
            "bullish": sum(1 for item in articles if item.get("sentiment_label") == "bullish"),
            "bearish": sum(1 for item in articles if item.get("sentiment_label") == "bearish"),
            "neutral": sum(1 for item in articles if item.get("sentiment_label") == "neutral"),
        },
        "key_events": [item.get("title") for item in articles[:5] if item.get("title")],
        "citations": [
            {
                "source_type": "news",
                "provider": item.get("provider") or item.get("source"),
                "title": item.get("title"),
                "url": item.get("url"),
                "published_at": item.get("published_at"),
                "ticker": ticker.upper(),
            }
            for item in articles
            if item.get("url") or item.get("title")
        ],
        "warnings": [] if articles else [f"No news found for {ticker.upper()} in window {normalized_window}."],
        "metadata": {
            "timestamp": stock_intelligence._now(),
            "providers_used": sorted({item.get("provider") or item.get("source") for item in articles if item.get("provider") or item.get("source")}),
        },
    }


@router.get("/{ticker}/earnings")
async def earnings(ticker: str):
    ticker = _ticker(ticker)
    return {"ticker": ticker.upper(), "history": [item.model_dump() for item in earnings_data.get_earnings_history(ticker)]}


@router.get("/{ticker}/next-earnings")
async def next_earnings(ticker: str):
    ticker = _ticker(ticker)
    event = earnings_data.get_next_earnings(ticker)
    return event.model_dump() if event else {"ticker": ticker.upper(), "event": None}


@router.get("/{ticker}/holders")
async def holders(ticker: str):
    ticker = _ticker(ticker)
    return get_fast_engine().get_holders(ticker)


@router.get("/{ticker}/filings")
async def filings(
    ticker: str,
    filing_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    ticker = _ticker(ticker)
    return {
        "ticker": ticker.upper(),
        "filings": get_fast_engine().get_filings(ticker, filing_type=filing_type, limit=limit),
    }


@router.get("/{ticker}/insiders")
async def insiders(ticker: str, limit: int = Query(50, ge=1, le=100)):
    ticker = _ticker(ticker)
    return {"ticker": ticker.upper(), "transactions": get_fast_engine().get_insider_trades(ticker, limit=limit)}


@router.get("/{ticker}/ai-summary")
async def ai_summary(ticker: str):
    ticker = _ticker(ticker)
    return get_fast_engine().answer_query(f"Summarize {ticker}")


@router.get("/{ticker}/summary")
async def summary(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_research_snapshot(ticker)
    return standard_response(
        {"ticker": ticker, "summary": payload["what_happened_today"], "snapshot": payload},
        citations=payload.get("citations", []),
        warnings=payload.get("warnings", []),
        mode="fast",
        intent="summary",
        providers_used=payload.get("providers_used", []),
        data_quality="partial" if payload.get("warnings") else "good",
    )


@router.get("/{ticker}/what-happened")
async def what_happened(ticker: str, window: str = Query("today")):
    ticker = _ticker(ticker)
    window = _window(window)
    payload = stock_intelligence.build_what_happened(ticker, window=window)
    return standard_response(
        payload,
        citations=payload.get("citations", []),
        warnings=payload.get("warnings", []),
        mode="fast",
        intent="what_happened",
        providers_used=payload.get("providers_used", []),
        data_quality="partial" if payload.get("warnings") else "good",
    )


@router.get("/{ticker}/sentiment")
async def sentiment(ticker: str, window: str = Query("today")):
    ticker = _ticker(ticker)
    window = _window(window)
    payload = get_stock_sentiment(ticker, window=window).model_dump()
    return standard_response(
        payload,
        citations=payload.get("citations", []),
        warnings=payload.get("warnings", []),
        mode="fast",
        intent="sentiment",
        providers_used=payload.get("providers_used", []),
        data_quality="partial" if payload.get("warnings") else "good",
    )


@router.get("/{ticker}/research-snapshot")
async def research_snapshot(ticker: str, window: str = Query("today")):
    ticker = _ticker(ticker)
    window = _window(window)
    payload = stock_intelligence.build_research_snapshot(ticker, window=window)
    return standard_response(
        payload,
        citations=payload.get("citations", []),
        warnings=payload.get("warnings", []),
        mode="fast",
        intent="research_snapshot",
        providers_used=payload.get("providers_used", []),
        data_quality="partial" if payload.get("warnings") else "good",
    )


@router.get("/{ticker}/risks")
async def risks(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_risks(ticker)
    return standard_response(payload, citations=payload.get("citations", []), warnings=payload.get("warnings", []), mode="fast", intent="risks")


@router.get("/{ticker}/bull-bear")
async def bull_bear(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_bull_bear(ticker)
    return standard_response(payload, citations=payload.get("citations", []), warnings=payload.get("warnings", []), mode="fast", intent="bull_bear")


@router.get("/{ticker}/earnings-brief")
async def earnings_brief(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_earnings_brief(ticker)
    return standard_response(payload, citations=payload.get("citations", []), warnings=payload.get("warnings", []), mode="fast", intent="earnings")


@router.get("/{ticker}/filing-brief")
async def filing_brief(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_filing_brief(ticker)
    return standard_response(payload, citations=payload.get("citations", []), warnings=payload.get("warnings", []), mode="fast", intent="filing")


@router.get("/{ticker}/investor-checklist")
async def investor_checklist(ticker: str):
    ticker = _ticker(ticker)
    payload = stock_intelligence.build_investor_checklist(ticker)
    return standard_response(payload, citations=payload.get("citations", []), warnings=payload.get("warnings", []), mode="fast", intent="investor_checklist")


@compat_router.get("/api/quote/{ticker}")
async def quote_compat(ticker: str):
    ticker = _ticker(ticker)
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


@compat_router.get("/api/compare")
async def compare(ticker_a: str = Query(...), ticker_b: str = Query(...)):
    left = _ticker(ticker_a)
    right = _ticker(ticker_b)
    payload = stock_intelligence.compare_stocks(left, right)
    return standard_response(
        payload,
        citations=payload.get("citations", []),
        warnings=payload.get("warnings", []),
        mode="fast",
        intent="comparison",
        data_quality="partial" if payload.get("warnings") else "good",
    )

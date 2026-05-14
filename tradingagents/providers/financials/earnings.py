"""Free earnings calendar and surprise data."""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import requests
from pydantic import BaseModel, Field

from tradingagents.infra.cache.sqlite import get_default_cache
import tradingagents.providers.demo.provider as demo_provider

logger = logging.getLogger(__name__)

CALENDAR_TTL = 60 * 60
HISTORY_TTL = 6 * 60 * 60


class EarningsEvent(BaseModel):
    ticker: str
    company_name: str | None = None
    report_date: str | None = None
    time_of_day: str = "unknown"
    estimated_eps: float | None = None
    consensus_revenue_estimate: float | None = None
    source: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class EarningsSurprise(BaseModel):
    ticker: str
    fiscal_period: str | None = None
    report_date: str | None = None
    actual_eps: float | None = None
    estimated_eps: float | None = None
    surprise_pct: float | None = None
    beat_miss: str = "unknown"
    source: str = "unknown"


class EarningsSurpriseStats(BaseModel):
    ticker: str
    quarters: int = 0
    beat_rate: float | None = None
    miss_rate: float | None = None
    average_surprise_pct: float | None = None
    source: str = "free_earnings_data"
    warnings: list[str] = Field(default_factory=list)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _get_json(url: str, params: dict[str, Any], retries: int = 2) -> Any | None:
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=(5, 15))
            if response.status_code in {401, 403, 404}:
                return None
            if response.status_code in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))
    logger.debug("Earnings provider failed for %s: %s", url, last_error)
    return None


def _normalize_hour(value: Any) -> str:
    text = str(value or "").lower()
    if text in {"bmo", "before market open", "amc", "after market close"}:
        return "BMO" if text.startswith(("bmo", "before")) else "AMC"
    return "unknown"


def _finnhub_calendar(start_date: str, end_date: str, tickers: list[str] | None) -> list[EarningsEvent]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []
    data = _get_json(
        "https://finnhub.io/api/v1/calendar/earnings",
        {"from": start_date, "to": end_date, "token": api_key},
    )
    rows = data.get("earningsCalendar") if isinstance(data, dict) else []
    selected = {ticker.upper() for ticker in tickers or []}
    events = []
    for item in rows or []:
        symbol = str(item.get("symbol") or "").upper()
        if selected and symbol not in selected:
            continue
        events.append(
            EarningsEvent(
                ticker=symbol,
                company_name=item.get("company"),
                report_date=item.get("date"),
                time_of_day=_normalize_hour(item.get("hour")),
                estimated_eps=_safe_float(item.get("epsEstimate")),
                consensus_revenue_estimate=_safe_float(item.get("revenueEstimate")),
                source="Finnhub",
            )
        )
    return events


def get_earnings_calendar(
    start_date: str | None = None,
    end_date: str | None = None,
    tickers: list[str] | None = None,
) -> list[EarningsEvent]:
    today = date.today()
    start = start_date or today.isoformat()
    end = end_date or (today + timedelta(days=30)).isoformat()
    selected = [ticker.upper().strip() for ticker in tickers or [] if ticker.strip()]
    if demo_provider.is_demo_mode() and selected:
        events = []
        for ticker in selected:
            demo = demo_provider.get_demo_earnings(ticker)
            if demo and demo.get("next"):
                events.append(EarningsEvent.model_validate(demo["next"]))
        return events
    cache = get_default_cache()
    key = f"{start}:{end}:{','.join(selected)}"
    cached = cache.get("earnings_calendar", key)
    if cached is not None:
        return [EarningsEvent.model_validate(item) for item in cached]
    events = _finnhub_calendar(start, end, selected)
    if not events and selected:
        events = [event for ticker in selected if (event := _yfinance_next_earnings(ticker)) is not None]
    cache.set("earnings_calendar", key, [event.model_dump() for event in events], ttl_seconds=CALENDAR_TTL)
    return events


def _finnhub_history(ticker: str) -> list[EarningsSurprise]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []
    data = _get_json(
        "https://finnhub.io/api/v1/stock/earnings",
        {"symbol": ticker.upper(), "token": api_key},
    )
    if not isinstance(data, list):
        return []
    rows = []
    for item in data:
        actual = _safe_float(item.get("actual"))
        estimate = _safe_float(item.get("estimate"))
        surprise = _safe_float(item.get("surprisePercent"))
        if surprise is None and actual is not None and estimate not in (None, 0):
            surprise = (actual - estimate) / abs(estimate) * 100
        beat_miss = "unknown"
        if actual is not None and estimate is not None:
            beat_miss = "beat" if actual > estimate else "miss" if actual < estimate else "inline"
        rows.append(
            EarningsSurprise(
                ticker=ticker.upper(),
                fiscal_period=item.get("period"),
                report_date=item.get("period") or item.get("date"),
                actual_eps=actual,
                estimated_eps=estimate,
                surprise_pct=surprise,
                beat_miss=beat_miss,
                source="Finnhub",
            )
        )
    return rows


def _yfinance_history(ticker: str, limit: int) -> list[EarningsSurprise]:
    try:
        import yfinance as yf

        dates = getattr(yf.Ticker(ticker.upper()), "earnings_dates", None)
    except Exception:
        return []
    if dates is None or getattr(dates, "empty", True):
        return []
    rows = []
    frame = dates.reset_index()
    for _, row in frame.head(limit).iterrows():
        actual = _safe_float(row.get("Reported EPS"))
        estimate = _safe_float(row.get("EPS Estimate"))
        surprise = _safe_float(row.get("Surprise(%)"))
        beat_miss = "unknown"
        if actual is not None and estimate is not None:
            beat_miss = "beat" if actual > estimate else "miss" if actual < estimate else "inline"
        rows.append(
            EarningsSurprise(
                ticker=ticker.upper(),
                report_date=str(row.iloc[0]),
                actual_eps=actual,
                estimated_eps=estimate,
                surprise_pct=surprise,
                beat_miss=beat_miss,
                source="yfinance",
            )
        )
    return rows


def get_earnings_history(ticker: str, limit: int = 8) -> list[EarningsSurprise]:
    symbol = ticker.upper().strip()
    if demo_provider.is_demo_mode():
        demo = demo_provider.get_demo_earnings(symbol)
        if demo:
            return [EarningsSurprise.model_validate(item) for item in demo["history"][:limit]]
    cache = get_default_cache()
    key = f"{symbol}:{limit}"
    cached = cache.get("earnings_history", key)
    if cached is not None:
        return [EarningsSurprise.model_validate(item) for item in cached]
    history = _finnhub_history(symbol)[:limit] or _yfinance_history(symbol, limit=limit)
    cache.set("earnings_history", key, [item.model_dump() for item in history], ttl_seconds=HISTORY_TTL)
    return history


def _yfinance_next_earnings(symbol: str) -> EarningsEvent | None:
    try:
        import yfinance as yf

        cal = getattr(yf.Ticker(symbol), "calendar", None)
        if isinstance(cal, dict):
            date_value = cal.get("Earnings Date")
            if isinstance(date_value, list):
                date_value = date_value[0]
            return EarningsEvent(
                ticker=symbol,
                report_date=str(date_value) if date_value else None,
                estimated_eps=_safe_float(cal.get("Earnings Average")),
                source="yfinance",
            )
        if hasattr(cal, "empty") and not cal.empty:
            value = cal.iloc[0, 0]
            return EarningsEvent(ticker=symbol, report_date=str(value), source="yfinance")
    except Exception:
        return None
    return None


def get_next_earnings(ticker: str) -> EarningsEvent | None:
    symbol = ticker.upper().strip()
    if demo_provider.is_demo_mode():
        demo = demo_provider.get_demo_earnings(symbol)
        if demo:
            return EarningsEvent.model_validate(demo["next"])
    events = get_earnings_calendar(tickers=[symbol])
    future = [event for event in events if event.report_date]
    if future:
        return sorted(future, key=lambda event: event.report_date or "")[0]
    return _yfinance_next_earnings(symbol)


def get_earnings_surprise_stats(ticker: str) -> EarningsSurpriseStats:
    history = get_earnings_history(ticker, limit=8)
    if not history:
        return EarningsSurpriseStats(ticker=ticker.upper(), warnings=["No earnings surprise history available."])
    beats = sum(1 for item in history if item.beat_miss == "beat")
    misses = sum(1 for item in history if item.beat_miss == "miss")
    surprises = [item.surprise_pct for item in history if item.surprise_pct is not None]
    return EarningsSurpriseStats(
        ticker=ticker.upper(),
        quarters=len(history),
        beat_rate=beats / len(history),
        miss_rate=misses / len(history),
        average_surprise_pct=sum(surprises) / len(surprises) if surprises else None,
    )

"""Real-time-ish free US market data aggregation."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import DEFAULT_TTLS, get_default_cache
from tradingagents.dataflows.free_provider_fallbacks import (
    get_alpha_vantage_quote,
    get_finnhub_quote,
)

logger = logging.getLogger(__name__)

QUOTE_TTL = 60
INDICES_TTL = 30
MOVERS_TTL = 120
BREADTH_TTL = 300
SECTORS_TTL = 300
MAX_BATCH_QUOTES = 50

INDEX_SYMBOLS = {
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
    "DIA": "SPDR Dow Jones Industrial Average ETF Trust",
    "IWM": "iShares Russell 2000 ETF",
    "^VIX": "CBOE Volatility Index",
}

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QuoteData(BaseModel):
    ticker: str
    price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    avg_volume: float | None = None
    previous_close: float | None = None
    source: str = "unknown"
    timestamp: str = Field(default_factory=utc_now_iso)
    warnings: list[str] = Field(default_factory=list)


class IndexData(QuoteData):
    symbol: str | None = None
    name: str | None = None


class MoversData(BaseModel):
    gainers: list[QuoteData] = Field(default_factory=list)
    losers: list[QuoteData] = Field(default_factory=list)
    source: str = "free_market_data"
    timestamp: str = Field(default_factory=utc_now_iso)
    warnings: list[str] = Field(default_factory=list)


class BreadthData(BaseModel):
    advancing: int = 0
    declining: int = 0
    unchanged: int = 0
    total: int = 0
    source: str = "free_market_data"
    timestamp: str = Field(default_factory=utc_now_iso)
    warnings: list[str] = Field(default_factory=list)


class SectorData(BaseModel):
    sector: str
    ticker: str
    price: float | None = None
    change_pct: float | None = None
    source: str = "free_market_data"
    timestamp: str = Field(default_factory=utc_now_iso)
    warnings: list[str] = Field(default_factory=list)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _retry(callable_obj, attempts: int = 3, base_delay: float = 0.5):
    last_error = None
    for attempt in range(attempts):
        try:
            return callable_obj()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(base_delay * (2**attempt))
    raise last_error


def _quote_from_fallback(ticker: str, fallback: dict[str, Any]) -> QuoteData:
    return QuoteData(
        ticker=ticker.upper(),
        price=_safe_float(fallback.get("price")),
        change=_safe_float(fallback.get("change")),
        change_pct=_safe_float(fallback.get("change_pct")),
        volume=_safe_float(fallback.get("volume")),
        day_high=_safe_float(fallback.get("day_high")),
        day_low=_safe_float(fallback.get("day_low")),
        previous_close=_safe_float(fallback.get("previous_close")),
        source=str(fallback.get("source") or "provider_fallback"),
    )


def _quote_from_yfinance(ticker: str) -> QuoteData:
    import yfinance as yf

    symbol = ticker.upper().strip()
    stock = yf.Ticker(symbol)
    fast_info = getattr(stock, "fast_info", None)
    info: dict[str, Any] = {}
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    def fast(name: str) -> Any:
        if fast_info is None:
            return None
        if hasattr(fast_info, name):
            return getattr(fast_info, name)
        try:
            return fast_info.get(name)
        except Exception:
            return None

    price = _safe_float(fast("last_price")) or _safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    previous = _safe_float(fast("previous_close")) or _safe_float(info.get("previousClose"))
    change = price - previous if price is not None and previous not in (None, 0) else None
    change_pct = change / previous * 100 if change is not None and previous else None
    return QuoteData(
        ticker=symbol,
        price=price,
        change=change,
        change_pct=change_pct,
        volume=_safe_float(info.get("volume") or fast("last_volume")),
        market_cap=_safe_float(info.get("marketCap") or fast("market_cap")),
        day_high=_safe_float(info.get("dayHigh") or fast("day_high")),
        day_low=_safe_float(info.get("dayLow") or fast("day_low")),
        fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh") or fast("year_high")),
        fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow") or fast("year_low")),
        avg_volume=_safe_float(info.get("averageVolume") or fast("ten_day_average_volume")),
        previous_close=previous,
        source="yfinance",
    )


def get_quote(ticker: str) -> QuoteData:
    """Return a cache-first quote with yfinance/Finnhub/Alpha Vantage fallbacks."""

    symbol = ticker.upper().strip()
    cache = get_default_cache()
    cached = cache.get("quotes", symbol)
    if cached is not None:
        return QuoteData.model_validate(cached)

    warnings: list[str] = []
    try:
        quote = _retry(lambda: _quote_from_yfinance(symbol))
        if quote.price is not None:
            cache.set("quotes", symbol, quote.model_dump(), ttl_seconds=QUOTE_TTL)
            return quote
        warnings.append("yfinance returned no price")
    except Exception as exc:
        warnings.append(f"yfinance quote failed: {exc}")

    for provider in (get_finnhub_quote, get_alpha_vantage_quote):
        try:
            fallback = provider(symbol)
            if fallback:
                quote = _quote_from_fallback(symbol, fallback)
                quote.warnings.extend(warnings)
                cache.set("quotes", symbol, quote.model_dump(), ttl_seconds=QUOTE_TTL)
                return quote
        except Exception as exc:
            warnings.append(f"{provider.__name__} failed: {exc}")

    stale = cache.get_stale("quotes", symbol)
    if stale:
        quote = QuoteData.model_validate(stale)
        quote.warnings.append("Returned stale cached quote after live sources failed.")
        return quote

    return QuoteData(ticker=symbol, source="unavailable", warnings=warnings or ["No quote source returned data."])


def _quote_from_history(symbol: str, frame: pd.DataFrame) -> QuoteData:
    if frame is None or frame.empty:
        return QuoteData(ticker=symbol, source="yfinance_batch", warnings=["No batch price data."])
    close = pd.to_numeric(frame.get("Close"), errors="coerce").dropna()
    if close.empty:
        return QuoteData(ticker=symbol, source="yfinance_batch", warnings=["No close prices in batch data."])
    price = _safe_float(close.iloc[-1])
    previous = _safe_float(close.iloc[-2]) if len(close) > 1 else None
    change = price - previous if price is not None and previous not in (None, 0) else None
    change_pct = change / previous * 100 if change is not None and previous else None
    return QuoteData(
        ticker=symbol,
        price=price,
        previous_close=previous,
        change=change,
        change_pct=change_pct,
        volume=_safe_float(frame.get("Volume").iloc[-1]) if "Volume" in frame else None,
        day_high=_safe_float(frame.get("High").iloc[-1]) if "High" in frame else None,
        day_low=_safe_float(frame.get("Low").iloc[-1]) if "Low" in frame else None,
        source="yfinance_batch",
    )


def get_batch_quotes(tickers: list[str]) -> dict[str, QuoteData]:
    symbols = [ticker.upper().strip() for ticker in tickers if ticker.strip()][:MAX_BATCH_QUOTES]
    cache = get_default_cache()
    result: dict[str, QuoteData] = {}
    missing: list[str] = []
    for symbol in symbols:
        cached = cache.get("quotes", symbol)
        if cached is not None:
            result[symbol] = QuoteData.model_validate(cached)
        else:
            missing.append(symbol)

    if missing:
        try:
            import yfinance as yf

            data = _retry(
                lambda: yf.download(
                    missing,
                    period="5d",
                    interval="1d",
                    group_by="ticker",
                    progress=False,
                    auto_adjust=False,
                    threads=True,
                )
            )
            for symbol in missing:
                try:
                    frame = data[symbol] if len(missing) > 1 and symbol in data.columns.get_level_values(0) else data
                    quote = _quote_from_history(symbol, frame)
                    result[symbol] = quote
                    cache.set("quotes", symbol, quote.model_dump(), ttl_seconds=QUOTE_TTL)
                except Exception as exc:
                    result[symbol] = get_quote(symbol)
                    result[symbol].warnings.append(f"Batch quote parse failed: {exc}")
        except Exception as exc:
            for symbol in missing:
                quote = get_quote(symbol)
                quote.warnings.append(f"Batch yfinance failed: {exc}")
                result[symbol] = quote
    return result


def get_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    import yfinance as yf

    return _retry(lambda: yf.Ticker(ticker.upper().strip()).history(period=period, interval=interval))


def get_intraday(ticker: str, interval: str = "5m") -> pd.DataFrame:
    return get_ohlcv(ticker, period="1d", interval=interval)


def get_market_indices() -> list[IndexData]:
    cache = get_default_cache()
    cached = cache.get("indices", "phase2_indices")
    if cached is not None:
        return [IndexData.model_validate(item) for item in cached]
    rows = []
    quotes = get_batch_quotes(list(INDEX_SYMBOLS.keys()))
    for symbol, name in INDEX_SYMBOLS.items():
        quote = quotes.get(symbol, QuoteData(ticker=symbol, warnings=["Missing index quote."]))
        rows.append(IndexData(**quote.model_dump(), symbol=symbol, name=name))
    cache.set("indices", "phase2_indices", [row.model_dump() for row in rows], ttl_seconds=INDICES_TTL)
    return rows


def load_universe(limit: int | None = None) -> list[str]:
    path = Path(__file__).resolve().parents[1] / "data" / "us_equity_universe.json"
    try:
        symbols = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "JPM", "XOM", "UNH", "SPY"]
    cleaned = []
    for symbol in symbols:
        ticker = str(symbol).upper().strip()
        if ticker and ticker not in cleaned:
            cleaned.append(ticker)
    return cleaned[:limit] if limit else cleaned


def get_market_movers(n: int = 10) -> MoversData:
    cache = get_default_cache()
    key = f"movers:{n}"
    cached = cache.get("market_movers", key)
    if cached is not None:
        return MoversData.model_validate(cached)
    warnings: list[str] = []
    quotes: list[QuoteData] = []
    universe = load_universe(limit=500)
    for start in range(0, len(universe), MAX_BATCH_QUOTES):
        batch = universe[start : start + MAX_BATCH_QUOTES]
        try:
            quotes.extend(get_batch_quotes(batch).values())
        except Exception as exc:
            warnings.append(f"Batch {start // MAX_BATCH_QUOTES + 1} failed: {exc}")
    ranked = [quote for quote in quotes if quote.change_pct is not None]
    gainers = sorted(ranked, key=lambda quote: quote.change_pct or 0, reverse=True)[:n]
    losers = sorted(ranked, key=lambda quote: quote.change_pct or 0)[:n]
    payload = MoversData(gainers=gainers, losers=losers, warnings=warnings)
    cache.set("market_movers", key, payload.model_dump(), ttl_seconds=MOVERS_TTL)
    return payload


def get_market_breadth() -> BreadthData:
    cache = get_default_cache()
    cached = cache.get("market_breadth", "default")
    if cached is not None:
        return BreadthData.model_validate(cached)
    quotes: list[QuoteData] = []
    universe = load_universe(limit=500)
    warnings: list[str] = []
    for start in range(0, len(universe), MAX_BATCH_QUOTES):
        batch = universe[start : start + MAX_BATCH_QUOTES]
        try:
            quotes.extend(get_batch_quotes(batch).values())
        except Exception as exc:
            warnings.append(f"Batch {start // MAX_BATCH_QUOTES + 1} failed: {exc}")
    advancing = declining = unchanged = 0
    for quote in quotes:
        if quote.change_pct is None:
            warnings.extend(quote.warnings)
            continue
        if quote.change_pct > 0:
            advancing += 1
        elif quote.change_pct < 0:
            declining += 1
        else:
            unchanged += 1
    payload = BreadthData(
        advancing=advancing,
        declining=declining,
        unchanged=unchanged,
        total=advancing + declining + unchanged,
        warnings=warnings[:10],
    )
    cache.set("market_breadth", "default", payload.model_dump(), ttl_seconds=BREADTH_TTL)
    return payload


def get_sector_performance() -> list[SectorData]:
    cache = get_default_cache()
    cached = cache.get("sector_performance", "default")
    if cached is not None:
        return [SectorData.model_validate(item) for item in cached]
    quotes = get_batch_quotes(list(SECTOR_ETFS.keys()))
    rows = []
    for ticker, sector in SECTOR_ETFS.items():
        quote = quotes.get(ticker, QuoteData(ticker=ticker, warnings=["Missing sector quote."]))
        rows.append(
            SectorData(
                sector=sector,
                ticker=ticker,
                price=quote.price,
                change_pct=quote.change_pct,
                source=quote.source,
                warnings=quote.warnings,
            )
        )
    cache.set("sector_performance", "default", [row.model_dump() for row in rows], ttl_seconds=SECTORS_TTL)
    return rows


def ohlcv_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    records = []
    data = frame.reset_index()
    for _, row in data.iterrows():
        records.append(
            {
                "date": str(row.iloc[0]),
                "open": _safe_float(row.get("Open")),
                "high": _safe_float(row.get("High")),
                "low": _safe_float(row.get("Low")),
                "close": _safe_float(row.get("Close")),
                "volume": _safe_float(row.get("Volume")),
            }
        )
    return records

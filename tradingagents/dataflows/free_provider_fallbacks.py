"""Optional free-tier provider fallbacks loaded from environment keys.

SEC and yfinance remain the primary backend data sources. These helpers use
already-configured keys only when present and only for simple free-tier style
endpoints. They never require a new paid dependency and never log API keys.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = float(os.getenv("TRADINGAGENTS_VENDOR_TIMEOUT", "8"))


def _get_json(
    url: str,
    *,
    params: dict[str, Any],
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = 1,
) -> Any | None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code in {401, 403, 404}:
                return None
            if response.status_code in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"provider returned HTTP {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
    logger.debug("Optional provider fallback failed for %s: %s", url, last_error)
    return None


def get_finnhub_quote(ticker: str) -> dict[str, Any] | None:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    data = _get_json(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": ticker.upper(), "token": api_key},
    )
    if not isinstance(data, dict) or not data.get("c"):
        return None
    price = data.get("c")
    previous = data.get("pc")
    change = data.get("d")
    change_pct = data.get("dp")
    return {
        "ticker": ticker.upper(),
        "price": price,
        "previous_close": previous,
        "change": change,
        "change_pct": change_pct,
        "open": data.get("o"),
        "day_high": data.get("h"),
        "day_low": data.get("l"),
        "as_of": data.get("t"),
        "source": "finnhub_free_tier",
    }


def get_alpha_vantage_quote(ticker: str) -> dict[str, Any] | None:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return None
    data = _get_json(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": ticker.upper(), "apikey": api_key},
    )
    quote = data.get("Global Quote") if isinstance(data, dict) else None
    if not quote:
        return None

    def number(key: str) -> float | None:
        try:
            raw = str(quote.get(key, "")).replace("%", "")
            return float(raw) if raw else None
        except Exception:
            return None

    price = number("05. price")
    previous = number("08. previous close")
    return {
        "ticker": ticker.upper(),
        "price": price,
        "previous_close": previous,
        "change": number("09. change"),
        "change_pct": number("10. change percent"),
        "open": number("02. open"),
        "day_high": number("03. high"),
        "day_low": number("04. low"),
        "volume": number("06. volume"),
        "latest_trading_day": quote.get("07. latest trading day"),
        "source": "alpha_vantage_free_tier",
    }


def get_provider_quote_fallback(ticker: str) -> dict[str, Any] | None:
    """Return a quote from an already-configured free-tier provider."""

    return get_finnhub_quote(ticker) or get_alpha_vantage_quote(ticker)


def get_alpha_vantage_overview(ticker: str) -> dict[str, Any] | None:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return None
    data = _get_json(
        "https://www.alphavantage.co/query",
        params={"function": "OVERVIEW", "symbol": ticker.upper(), "apikey": api_key},
    )
    if not isinstance(data, dict) or not data.get("Symbol"):
        return None
    return {
        "ticker": data.get("Symbol", ticker.upper()),
        "name": data.get("Name"),
        "exchange": data.get("Exchange"),
        "sector": data.get("Sector"),
        "industry": data.get("Industry"),
        "summary": data.get("Description"),
        "market_cap": _maybe_number(data.get("MarketCapitalization")),
        "pe": _maybe_number(data.get("PERatio")),
        "peg": _maybe_number(data.get("PEGRatio")),
        "eps": _maybe_number(data.get("EPS")),
        "source": "alpha_vantage_free_tier",
    }


def get_fmp_profile(ticker: str) -> dict[str, Any] | None:
    api_key = os.getenv("FINANCIAL_MODELING_PREP_API_KEY")
    if not api_key:
        return None
    data = _get_json(
        f"https://financialmodelingprep.com/api/v3/profile/{ticker.upper()}",
        params={"apikey": api_key},
    )
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    return {
        "ticker": item.get("symbol", ticker.upper()),
        "name": item.get("companyName"),
        "exchange": item.get("exchangeShortName") or item.get("exchange"),
        "sector": item.get("sector"),
        "industry": item.get("industry"),
        "website": item.get("website"),
        "summary": item.get("description"),
        "market_cap": item.get("mktCap"),
        "price": item.get("price"),
        "source": "fmp_existing_key",
    }


def get_provider_profile_fallback(ticker: str) -> dict[str, Any] | None:
    """Return company profile fields from already-configured fallback providers."""

    return get_alpha_vantage_overview(ticker) or get_fmp_profile(ticker)


def _maybe_number(value: Any) -> float | None:
    try:
        if value in (None, "", "None", "N/A", "-"):
            return None
        return float(value)
    except Exception:
        return None

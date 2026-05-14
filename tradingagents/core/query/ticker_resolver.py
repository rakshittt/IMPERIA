"""Ticker/company lookup for supported US equities and major US ETFs."""

from __future__ import annotations

import difflib
import re
from functools import lru_cache
from typing import Any


MAJOR_US_ETFS: dict[str, dict[str, str]] = {
    "SPY": {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "exchange": "NYSE Arca", "security_type": "ETF"},
    "IVV": {"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "exchange": "NYSE Arca", "security_type": "ETF"},
    "VOO": {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "exchange": "NYSE Arca", "security_type": "ETF"},
    "QQQ": {"ticker": "QQQ", "name": "Invesco QQQ Trust", "exchange": "NASDAQ", "security_type": "ETF"},
    "DIA": {"ticker": "DIA", "name": "SPDR Dow Jones Industrial Average ETF Trust", "exchange": "NYSE Arca", "security_type": "ETF"},
    "IWM": {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "exchange": "NYSE Arca", "security_type": "ETF"},
    "VTI": {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "exchange": "NYSE Arca", "security_type": "ETF"},
    "XLK": {"ticker": "XLK", "name": "Technology Select Sector SPDR Fund", "exchange": "NYSE Arca", "security_type": "ETF"},
    "XLF": {"ticker": "XLF", "name": "Financial Select Sector SPDR Fund", "exchange": "NYSE Arca", "security_type": "ETF"},
    "XLE": {"ticker": "XLE", "name": "Energy Select Sector SPDR Fund", "exchange": "NYSE Arca", "security_type": "ETF"},
    "XLV": {"ticker": "XLV", "name": "Health Care Select Sector SPDR Fund", "exchange": "NYSE Arca", "security_type": "ETF"},
}

POPULAR_US_SYMBOLS: dict[str, dict[str, str]] = {
    "AAPL": {"ticker": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "MSFT": {"ticker": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "security_type": "Equity"},
    "NVDA": {"ticker": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ", "security_type": "Equity"},
    "TSLA": {"ticker": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "AMZN": {"ticker": "AMZN", "name": "Amazon.com, Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "GOOGL": {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "exchange": "NASDAQ", "security_type": "Equity"},
    "GOOG": {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "exchange": "NASDAQ", "security_type": "Equity"},
    "META": {"ticker": "META", "name": "Meta Platforms, Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "AMD": {"ticker": "AMD", "name": "Advanced Micro Devices, Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "NFLX": {"ticker": "NFLX", "name": "Netflix, Inc.", "exchange": "NASDAQ", "security_type": "Equity"},
    "JPM": {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE", "security_type": "Equity"},
    "BRK-B": {"ticker": "BRK-B", "name": "Berkshire Hathaway Inc. Class B", "exchange": "NYSE", "security_type": "Equity"},
    "UNH": {"ticker": "UNH", "name": "UnitedHealth Group Incorporated", "exchange": "NYSE", "security_type": "Equity"},
    "XOM": {"ticker": "XOM", "name": "Exxon Mobil Corporation", "exchange": "NYSE", "security_type": "Equity"},
    "LLY": {"ticker": "LLY", "name": "Eli Lilly and Company", "exchange": "NYSE", "security_type": "Equity"},
}

COMMON_ALIASES = {
    "APPLE": "AAPL",
    "APPLE INC": "AAPL",
    "MICROSOFT": "MSFT",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "AMAZON": "AMZN",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "META": "META",
    "FACEBOOK": "META",
    "AMD": "AMD",
    "NETFLIX": "NFLX",
    "BERKSHIRE": "BRK-B",
    "S&P 500 ETF": "SPY",
    "SP500 ETF": "SPY",
    "NASDAQ 100 ETF": "QQQ",
}

_UNSUPPORTED_PATTERNS = (
    re.compile(r"^[A-Z]{6,}=X$"),
    re.compile(r"^[A-Z]{2,5}-USD$"),
    re.compile(r"^[A-Z]{2,5}/[A-Z]{2,5}$"),
)
_UNSUPPORTED_TERMS = {"BTC", "ETH", "DOGE", "SOL", "EURUSD", "USDJPY", "FOREX", "CRYPTO"}


def _normalize_query(query: str) -> str:
    value = query.strip().upper().replace(".", "-")
    value = re.sub(r"\s+", " ", value)
    return value


def _is_unsupported_market(query: str) -> bool:
    normalized = _normalize_query(query)
    if normalized in _UNSUPPORTED_TERMS:
        return True
    return any(pattern.match(normalized) for pattern in _UNSUPPORTED_PATTERNS)


@lru_cache(maxsize=1)
def _symbol_universe() -> list[dict[str, Any]]:
    universe: dict[str, dict[str, Any]] = {}
    universe.update(POPULAR_US_SYMBOLS)
    universe.update(MAJOR_US_ETFS)
    try:
        from tradingagents.providers.filings.edgar import load_sec_ticker_universe

        for entry in load_sec_ticker_universe():
            universe.setdefault(entry["ticker"], entry)
    except Exception:
        pass
    return list(universe.values())


def resolve_ticker(query: str) -> dict[str, Any]:
    """Resolve a ticker/company query to a supported US symbol."""

    raw = query.strip()
    if not raw:
        return {"query": query, "supported": False, "error": "empty query"}
    if _is_unsupported_market(raw):
        return {
            "query": query,
            "supported": False,
            "error": "Only US-listed equities and major US ETFs are supported.",
        }

    normalized = _normalize_query(raw)
    alias = COMMON_ALIASES.get(normalized)
    if alias:
        item = dict(POPULAR_US_SYMBOLS.get(alias) or MAJOR_US_ETFS.get(alias) or {})
        item.update({"query": query, "match_type": "alias", "confidence": 0.99, "supported": True})
        return item

    for item in _symbol_universe():
        if normalized == item["ticker"]:
            result = dict(item)
            result.update({"query": query, "match_type": "exact", "confidence": 1.0, "supported": True})
            return result

    matches = search_symbols(raw, limit=1)
    if matches and matches[0]["confidence"] >= 0.55:
        result = dict(matches[0])
        result.update({"query": query, "supported": True})
        return result
    return {
        "query": query,
        "supported": False,
        "error": "No supported US equity or major US ETF match found.",
    }


def search_symbols(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fuzzy search supported symbols and company names."""

    raw = query.strip()
    if not raw or _is_unsupported_market(raw):
        return []
    normalized = _normalize_query(raw)
    scored: list[dict[str, Any]] = []
    for item in _symbol_universe():
        ticker = item["ticker"]
        name = item.get("name", "")
        ticker_score = difflib.SequenceMatcher(None, normalized, ticker).ratio()
        name_score = difflib.SequenceMatcher(None, normalized, name.upper()).ratio()
        contains_bonus = 0.18 if normalized in name.upper() else 0
        prefix_bonus = 0.15 if ticker.startswith(normalized) or name.upper().startswith(normalized) else 0
        score = max(ticker_score, name_score + contains_bonus, prefix_bonus)
        if score >= 0.25:
            result = dict(item)
            result.update(
                {
                    "match_type": "fuzzy" if normalized != ticker else "exact",
                    "confidence": round(min(score, 1.0), 3),
                    "supported": True,
                }
            )
            scored.append(result)
    scored.sort(key=lambda item: (item["confidence"], item.get("security_type") == "Equity"), reverse=True)
    return scored[: max(1, limit)]

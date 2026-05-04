"""Lightweight parser for stock and market questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .ticker_resolver import resolve_ticker


@dataclass
class ParsedQuery:
    original: str
    intent: str
    tickers: list[str] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)


_TICKER_RE = re.compile(r"\b[A-Z]{1,5}(?:[.-][A-Z])?\b")


def parse_query(query: str) -> ParsedQuery:
    text = query.strip()
    lower = text.lower()
    intent = "general"
    if any(term in lower for term in ("market", "s&p", "nasdaq", "dow", "indices", "movers")):
        intent = "market_overview"
    if any(term in lower for term in ("news", "why", "happened", "up today", "down today")):
        intent = "news_query"
    if any(term in lower for term in ("earnings", "eps", "revenue", "quarter")):
        intent = "earnings"
    if any(term in lower for term in ("ratio", "p/e", "pe ", "margin", "roe", "roa", "debt")):
        intent = "ratios"
    if any(term in lower for term in ("compare", " vs ", " versus ", "over ")):
        intent = "comparison"
    if any(term in lower for term in ("portfolio", "bull", "bear", "long-term", "long term", "should i buy", "thesis")):
        intent = "deep_research"

    entities: list[dict] = []
    tickers: list[str] = []
    for candidate in _TICKER_RE.findall(text.upper()):
        resolved = resolve_ticker(candidate)
        if resolved.get("supported"):
            symbol = resolved["ticker"]
            if symbol not in tickers:
                tickers.append(symbol)
                entities.append(resolved)

    if not tickers:
        words = re.sub(r"[^A-Za-z0-9&. -]", " ", text)
        for phrase in (words, words.split("'")[0]):
            resolved = resolve_ticker(phrase)
            if resolved.get("supported"):
                tickers.append(resolved["ticker"])
                entities.append(resolved)
                break

    if intent == "general" and tickers:
        intent = "stock_lookup"
    return ParsedQuery(original=query, intent=intent, tickers=tickers, entities=entities)

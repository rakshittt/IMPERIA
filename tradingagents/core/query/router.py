"""Route natural-language finance questions to fast or deep research mode."""

from __future__ import annotations

from dataclasses import dataclass, field

from tradingagents.core.query.parser import parse_query


@dataclass
class QueryRoute:
    mode: str
    intent: str
    tickers: list[str] = field(default_factory=list)
    confidence: float = 0.75
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "intent": self.intent,
            "tickers": self.tickers,
            "confidence": self.confidence,
            "reason": self.reason,
        }


DEEP_TERMS = (
    "should i buy",
    "should i sell",
    "long-term",
    "long term",
    "portfolio",
    "bull vs bear",
    "bull/bear",
    "bull case",
    "bear case",
    "thesis",
    "value perspective",
    "deep research",
    "analyze",
    "evaluate",
)

FAST_TERMS = (
    "p/e",
    "pe ratio",
    "ratio",
    "quote",
    "price",
    "news",
    "why",
    "earnings",
    "market movers",
    "indices",
    "s&p 500",
    "nasdaq",
    "dow",
    "summary",
)


def route_query(query: str) -> QueryRoute:
    parsed = parse_query(query)
    lower = query.lower()
    if any(term in lower for term in DEEP_TERMS):
        if "earnings" not in lower and "summary" not in lower:
            return QueryRoute(
                mode="deep",
                intent=parsed.intent if parsed.intent != "general" else "deep_research",
                tickers=parsed.tickers,
                confidence=0.9,
                reason="Question asks for investment judgment, comparison, portfolio analysis, or thesis work.",
            )
    if parsed.intent == "comparison" and len(parsed.tickers) >= 2:
        return QueryRoute(
            mode="deep",
            intent="comparison",
            tickers=parsed.tickers,
            confidence=0.88,
            reason="Comparative investment analysis is routed to the deep research engine.",
        )
    if any(term in lower for term in FAST_TERMS) or parsed.intent in {
        "stock_lookup",
        "news_query",
        "market_overview",
        "earnings",
        "ratios",
    }:
        return QueryRoute(
            mode="fast",
            intent=parsed.intent,
            tickers=parsed.tickers,
            confidence=0.84,
            reason="Question can be answered from cached/live market, news, SEC, and computed data.",
        )
    if parsed.tickers:
        return QueryRoute(
            mode="fast",
            intent="stock_lookup",
            tickers=parsed.tickers,
            confidence=0.72,
            reason="Single-symbol lookup defaults to fast mode.",
        )
    return QueryRoute(
        mode="fast",
        intent=parsed.intent,
        tickers=[],
        confidence=0.55,
        reason="No deep-research trigger detected; using fast general market handling.",
    )

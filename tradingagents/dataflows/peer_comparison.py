"""Peer-basket comparison helpers for IMPERIA expert research."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.dataflows import demo_provider, market_data
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.utils.validation import normalize_ticker

STATIC_PEERS: dict[str, list[str]] = {
    "AAPL": ["MSFT", "GOOGL", "AMZN", "META"],
    "MSFT": ["AAPL", "GOOGL", "ORCL", "CRM"],
    "NVDA": ["AMD", "AVGO", "QCOM", "TSM"],
    "AMD": ["NVDA", "INTC", "QCOM", "AVGO"],
    "TSLA": ["GM", "F", "RIVN", "LCID"],
    "JPM": ["BAC", "WFC", "C", "GS"],
    "XOM": ["CVX", "COP", "SLB", "EOG"],
    "SPY": ["QQQ", "DIA", "IWM", "VOO"],
    "QQQ": ["SPY", "XLK", "VGT", "IWM"],
}


class PeerMetric(BaseModel):
    ticker: str
    price_change_pct: float | None = None
    market_cap: float | None = None
    pe: float | None = None
    revenue_growth: float | None = None
    net_margin: float | None = None
    roe: float | None = None


class PeerComparison(BaseModel):
    ticker: str
    peers: list[PeerMetric] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def resolve_peer_basket(ticker: str, limit: int = 5) -> list[str]:
    symbol = normalize_ticker(ticker)
    peers = STATIC_PEERS.get(symbol)
    if peers:
        return peers[:limit]
    universe = demo_provider.demo_universe()
    if symbol in universe:
        start = max(0, universe.index(symbol) - 2)
        return [candidate for candidate in universe[start : start + limit + 1] if candidate != symbol][:limit]
    return ["SPY", "QQQ", "DIA", "IWM"][:limit]


def get_peer_comparison(ticker: str, limit: int = 5) -> PeerComparison:
    """Return a conservative peer snapshot with partial-data warnings."""

    symbol = normalize_ticker(ticker)
    peers = resolve_peer_basket(symbol, limit=limit)
    warnings: list[str] = []
    rows: list[PeerMetric] = []
    citations: list[dict[str, Any]] = []
    for peer in peers:
        try:
            quote = market_data.get_quote(peer)
            metrics = compute_financial_metrics(peer)
            values = metrics.get("metrics", {})
            rows.append(
                PeerMetric(
                    ticker=peer,
                    price_change_pct=quote.change_pct,
                    market_cap=quote.market_cap,
                    pe=values.get("pe"),
                    revenue_growth=values.get("revenue_growth"),
                    net_margin=values.get("net_margin"),
                    roe=values.get("roe"),
                )
            )
            citations.append({"source_type": "peer_comparison", "provider": quote.source, "title": f"{peer} peer quote/metrics", "url": f"https://finance.yahoo.com/quote/{peer}", "ticker": peer})
        except Exception as exc:
            warnings.append(f"Peer {peer} unavailable ({type(exc).__name__}).")
    if not rows:
        warnings.append(f"No peer comparison data available for {symbol}.")
    return PeerComparison(ticker=symbol, peers=rows, warnings=warnings, citations=citations)

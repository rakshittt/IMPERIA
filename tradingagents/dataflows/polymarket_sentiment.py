"""Read-only Polymarket sentiment provider.

This module only reads public market/event data. It never handles wallets,
private keys, orders, deposits, withdrawals, or trading actions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows.demo_provider import demo_citation, get_demo_sentiment, is_demo_mode
from tradingagents.utils.http import safe_get_json

GAMMA_API_BASE = os.getenv("GAMMA_API_BASE", "https://gamma-api.polymarket.com")
DATA_API_BASE = os.getenv("DATA_API_BASE", "https://data-api.polymarket.com")
CLOB_API_BASE = os.getenv("CLOB_API_BASE", "https://clob.polymarket.com")
DEFAULT_TTL = int(os.getenv("POLYMARKET_CACHE_TTL_SECONDS", "300"))


class PolymarketSignal(BaseModel):
    market_title: str
    market_url: str | None = None
    probability: float | None = None
    volume: float | None = None
    liquidity: float | None = None
    relevance_score: float = 0
    interpretation: str


class PolymarketSentiment(BaseModel):
    provider: str = "polymarket"
    ticker: str
    company_name: str | None = None
    sentiment_label: str = "uncertain"
    confidence_score: int = 0
    summary: str
    signals: list[PolymarketSignal] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _aliases(ticker: str, company_name: str | None = None) -> list[str]:
    symbol = ticker.upper()
    aliases = [symbol]
    if company_name:
        aliases.append(company_name)
        aliases.append(company_name.split(",")[0])
    thematic = {
        "NVDA": ["Nvidia", "NVIDIA", "AI chips", "semiconductors", "Nvidia earnings"],
        "AMD": ["AMD", "Advanced Micro Devices", "AI chips", "semiconductors", "AMD earnings"],
        "AAPL": ["Apple", "iPhone", "Apple earnings", "Apple market cap"],
        "MSFT": ["Microsoft", "Azure", "Microsoft earnings", "AI software"],
        "TSLA": ["Tesla", "EV", "Tesla deliveries", "Tesla earnings"],
    }
    aliases.extend(thematic.get(symbol, []))
    seen = []
    for alias in aliases:
        if alias and alias not in seen:
            seen.append(alias)
    return seen


def _extract_markets(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("markets", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        if payload.get("type") == "market":
            return [payload]
    return []


def _score_market(market: dict[str, Any], aliases: list[str]) -> float:
    title = str(market.get("question") or market.get("title") or market.get("name") or "").lower()
    if not title:
        return 0
    score = 0.0
    for alias in aliases:
        alias_l = alias.lower()
        if alias_l in title:
            score = max(score, 0.9 if len(alias_l) <= 6 else 0.8)
        elif any(part and part in title for part in alias_l.split() if len(part) > 3):
            score = max(score, 0.55)
    finance_terms = ("earnings", "stock", "market cap", "revenue", "profit", "semiconductor", "iphone", "deliveries")
    if any(term in title for term in finance_terms):
        score += 0.08
    return min(score, 1.0)


def _maybe_probability(market: dict[str, Any]) -> float | None:
    raw = market.get("outcomePrices") or market.get("outcomesPrices") or market.get("prices")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    if isinstance(raw, list) and raw:
        try:
            values = [float(item) for item in raw if item is not None]
            return max(values) if values else None
        except Exception:
            return None
    for key in ("lastTradePrice", "bestAsk", "bestBid", "price"):
        try:
            if market.get(key) is not None:
                return float(market[key])
        except Exception:
            pass
    return None


def _safe_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "", "None") else None
    except Exception:
        return None


def _label_from_signals(signals: list[PolymarketSignal]) -> tuple[str, int, str]:
    if not signals:
        return "uncertain", 0, "No sufficiently relevant Polymarket markets found for this ticker."
    scored = [signal for signal in signals if signal.probability is not None]
    if not scored:
        return "uncertain", 30, "Relevant Polymarket markets were found, but no interpretable probability was available."
    weighted = sum((signal.probability or 0.5) * signal.relevance_score for signal in scored)
    denom = sum(signal.relevance_score for signal in scored) or 1
    probability = weighted / denom
    confidence = int(min(95, max(35, sum(signal.relevance_score for signal in scored) / len(scored) * 100)))
    if probability >= 0.6:
        return "bullish", confidence, "Polymarket-derived event signals lean positive, but this is not a stock recommendation."
    if probability <= 0.4:
        return "bearish", confidence, "Polymarket-derived event signals lean negative, but this is not a stock recommendation."
    return "mixed", confidence, "Polymarket-derived event signals are balanced or mixed."


def get_polymarket_sentiment(ticker: str, company_name: str | None = None) -> PolymarketSentiment:
    symbol = ticker.upper().replace(".", "-")
    if is_demo_mode():
        demo = get_demo_sentiment(symbol)
        if demo:
            return PolymarketSentiment(
                ticker=symbol,
                company_name=company_name,
                sentiment_label=demo["sentiment_label"],
                confidence_score=int(demo["confidence_score"]),
                summary=f"Demo Polymarket-style sentiment: {demo['summary']}",
                warnings=demo.get("warnings", []),
                citations=[demo_citation("prediction_market", f"{symbol} demo prediction-market sentiment", ticker=symbol)],
            )
    cache = get_default_cache()
    cache_key = f"{symbol}:{company_name or ''}"
    cached = cache.get("polymarket_sentiment", cache_key)
    if cached is not None:
        return PolymarketSentiment.model_validate(cached)

    aliases = _aliases(symbol, company_name)
    markets: list[dict[str, Any]] = []
    warnings: list[str] = []
    for alias in aliases[:6]:
        payload = safe_get_json(
            f"{GAMMA_API_BASE.rstrip('/')}/search",
            params={"query": alias, "type": "markets", "limit": 10},
            source="polymarket_gamma_search",
            attempts=3,
        )
        if payload is None:
            warnings.append(f"Polymarket search unavailable for {alias}.")
            continue
        markets.extend(_extract_markets(payload))

    deduped: dict[str, dict[str, Any]] = {}
    for market in markets:
        key = str(market.get("id") or market.get("conditionId") or market.get("slug") or market.get("question"))
        if key:
            deduped[key] = market

    signals: list[PolymarketSignal] = []
    citations: list[dict[str, Any]] = []
    for market in deduped.values():
        relevance = _score_market(market, aliases)
        if relevance < 0.5:
            continue
        title = str(market.get("question") or market.get("title") or market.get("name") or "Polymarket market")
        slug = market.get("slug")
        url = f"https://polymarket.com/event/{slug}" if slug else None
        probability = _maybe_probability(market)
        volume = _safe_float(market.get("volume") or market.get("volumeNum"))
        liquidity = _safe_float(market.get("liquidity") or market.get("liquidityNum"))
        signals.append(
            PolymarketSignal(
                market_title=title,
                market_url=url,
                probability=probability,
                volume=volume,
                liquidity=liquidity,
                relevance_score=round(relevance, 2),
                interpretation="Prediction-market signal is relevant but should be treated as alternative event-market context, not stock advice.",
            )
        )
        citations.append(
            {
                "source_type": "prediction_market",
                "provider": "Polymarket Gamma API",
                "title": title,
                "url": url,
                "ticker": symbol,
                "relevance_score": round(relevance, 2),
            }
        )

    label, confidence, summary = _label_from_signals(signals)
    if not signals:
        warnings.append("No sufficiently relevant Polymarket markets found for this ticker.")
    payload = PolymarketSentiment(
        ticker=symbol,
        company_name=company_name,
        sentiment_label=label,
        confidence_score=confidence,
        summary=summary,
        signals=signals[:5],
        warnings=warnings,
        citations=citations[:5],
    )
    cache.set("polymarket_sentiment", cache_key, payload.model_dump(), ttl_seconds=DEFAULT_TTL)
    return payload

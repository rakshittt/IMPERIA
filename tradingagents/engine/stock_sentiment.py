"""Combined stock sentiment engine for stock-first IMPERIA workflows."""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows import earnings_data, market_data, news_aggregator
from tradingagents.dataflows.polymarket_sentiment import get_polymarket_sentiment
from tradingagents.engine.safety import DISCLAIMER
from tradingagents.utils.validation import normalize_ticker


class StockSentiment(BaseModel):
    ticker: str
    company_name: str | None = None
    sentiment_label: str = "uncertain"
    confidence_score: int = 0
    time_window: str = "today"
    summary: str
    research_sentiment: str
    not_investment_advice: bool = True
    signals: dict[str, Any] = Field(default_factory=dict)
    what_solo_investors_should_watch: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    providers_used: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _score_label(score: float, signal_count: int) -> tuple[str, int]:
    if signal_count == 0:
        return "uncertain", 0
    confidence = int(min(92, max(35, 45 + abs(score) * 8 + signal_count * 5)))
    if score >= 2:
        return "bullish", confidence
    if score <= -2:
        return "bearish", confidence
    if abs(score) < 0.75:
        return "neutral", confidence
    return "mixed", confidence


def _news_score(articles: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    score = 0.0
    labels: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0, "mixed": 0}
    for article in articles:
        label = (article.get("sentiment_label") or article.get("sentiment") or "neutral").lower()
        if label in {"positive"}:
            label = "bullish"
        if label in {"negative"}:
            label = "bearish"
        if label not in labels:
            label = "neutral"
        labels[label] += 1
        score += 1 if label == "bullish" else -1 if label == "bearish" else 0
    return score, {"article_count": len(articles), "sentiment_counts": labels}


def get_stock_sentiment(ticker: str, *, window: str = "today") -> StockSentiment:
    symbol = normalize_ticker(ticker)
    window = news_aggregator.normalize_news_window(window)
    cache = get_default_cache()
    cache_key = f"{symbol}:{window}"
    cached = cache.get("stock_sentiment", cache_key)
    if cached is not None:
        return StockSentiment.model_validate(cached)

    warnings: list[str] = []
    citations: list[dict[str, Any]] = []
    providers: list[str] = []
    signals: dict[str, Any] = {}
    score = 0.0
    signal_count = 0

    quote = market_data.get_quote(symbol)
    providers.append(quote.source)
    warnings.extend(quote.warnings)
    price_signal = {
        "price": quote.price,
        "change_pct": quote.change_pct,
        "volume": quote.volume,
        "avg_volume": quote.avg_volume,
    }
    if quote.change_pct is not None:
        price_score = 1.5 if quote.change_pct > 1 else 0.5 if quote.change_pct > 0 else -1.5 if quote.change_pct < -1 else -0.5 if quote.change_pct < 0 else 0
        score += price_score
        signal_count += 1
        price_signal["score"] = price_score
    if quote.volume and quote.avg_volume:
        rel_volume = quote.volume / quote.avg_volume if quote.avg_volume else None
        price_signal["relative_volume"] = rel_volume
        if rel_volume and rel_volume > 1.5:
            signal_count += 1
    signals["price_action"] = price_signal
    citations.append({"source_type": "market_data", "provider": quote.source, "title": f"{symbol} quote", "url": f"https://finance.yahoo.com/quote/{symbol}", "ticker": symbol})

    try:
        articles = [item.model_dump() for item in news_aggregator.get_stock_news(symbol, limit=10, window=window)]
    except TypeError:
        articles = [item.model_dump() for item in news_aggregator.get_stock_news(symbol, limit=10)]
    news_delta, news_signal = _news_score(articles)
    if articles:
        score += news_delta
        signal_count += 1
        providers.extend(sorted({item.get("provider") or item.get("source") for item in articles if item.get("provider") or item.get("source")}))
        citations.extend(
            {
                "source_type": "news",
                "provider": item.get("provider") or item.get("source"),
                "title": item.get("title"),
                "url": item.get("url"),
                "published_at": item.get("published_at"),
                "ticker": symbol,
            }
            for item in articles[:5]
        )
    else:
        warnings.append(f"No news found for {symbol} in window {window}.")
    signals["news"] = news_signal

    try:
        stats = earnings_data.get_earnings_surprise_stats(symbol).model_dump()
        beat_rate = stats.get("beat_rate")
        if beat_rate is not None:
            score += 0.75 if beat_rate >= 0.6 else -0.75 if beat_rate <= 0.35 else 0
            signal_count += 1
        signals["earnings"] = stats
        providers.append(stats.get("source", "free_earnings_data"))
    except Exception as exc:
        warnings.append(f"Earnings sentiment unavailable ({type(exc).__name__}).")
        signals["earnings"] = {}

    try:
        sectors = [item.model_dump() for item in market_data.get_sector_performance()]
        sector_changes = [item.get("change_pct") for item in sectors if item.get("change_pct") is not None]
        sector_average = mean(sector_changes) if sector_changes else None
        if sector_average is not None:
            score += 0.5 if sector_average > 0.5 else -0.5 if sector_average < -0.5 else 0
            signal_count += 1
        signals["sector"] = {"average_change_pct": sector_average, "sectors": sectors[:5]}
        providers.append("sector_etf_yfinance")
    except Exception as exc:
        warnings.append(f"Sector context unavailable ({type(exc).__name__}).")
        signals["sector"] = {}

    try:
        poly = get_polymarket_sentiment(symbol, quote.ticker).model_dump()
        signals["polymarket"] = poly
        warnings.extend(poly.get("warnings", []))
        citations.extend(poly.get("citations", []))
        if poly.get("sentiment_label") == "bullish":
            score += 0.75
            signal_count += 1
        elif poly.get("sentiment_label") == "bearish":
            score -= 0.75
            signal_count += 1
        providers.append("polymarket")
    except Exception as exc:
        warnings.append(f"Polymarket sentiment unavailable ({type(exc).__name__}).")
        signals["polymarket"] = {}

    label, confidence = _score_label(score, signal_count)
    summary = (
        f"{symbol} research sentiment is {label} for {window}. "
        "This combines price action, news, earnings context, sector movement, and optional prediction-market signals. "
        f"{DISCLAIMER}"
    )
    result = StockSentiment(
        ticker=symbol,
        company_name=None,
        sentiment_label=label,
        confidence_score=confidence,
        time_window=window,
        summary=summary,
        research_sentiment=label,
        signals=signals,
        what_solo_investors_should_watch=[
            "Recent price move versus sector and market",
            "News catalysts and whether they are confirmed by filings or earnings",
            "Next earnings date and estimate revisions",
            "SEC risk factors and material 8-K updates",
        ],
        risks=[
            "Sentiment can change quickly when news or market context changes.",
            "Prediction-market signals may be indirect or unavailable.",
            "Free-provider data can be delayed, incomplete, or rate-limited.",
        ],
        warnings=warnings,
        citations=citations,
        providers_used=sorted({provider for provider in providers if provider}),
    )
    cache.set("stock_sentiment", cache_key, result.model_dump(), ttl_seconds=5 * 60)
    return result


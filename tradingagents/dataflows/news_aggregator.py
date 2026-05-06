"""Unified free-news aggregation for US stocks and markets."""

from __future__ import annotations

import logging
import os
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests
from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.engine.citation_tracker import CitationTracker
import tradingagents.dataflows.demo_provider as demo_provider

logger = logging.getLogger(__name__)

NEWS_TTL = 5 * 60


class NewsItem(BaseModel):
    title: str
    url: str | None = None
    source: str
    provider: str | None = None
    published_at: str | None = None
    summary: str | None = None
    snippet: str | None = None
    sentiment: str | None = None
    sentiment_label: str | None = None
    tickers_mentioned: list[str] = Field(default_factory=list)
    tickers: list[str] = Field(default_factory=list)
    citation_id: str | None = None


WINDOW_ALIASES = {
    "today": "today",
    "day": "today",
    "past_day": "past_day",
    "1d": "past_day",
    "past_week": "past_week",
    "week": "past_week",
    "7d": "past_week",
    "past_month": "past_month",
    "month": "past_month",
    "30d": "past_month",
}


def normalize_news_window(window: str | None = None) -> str:
    value = (window or "today").strip().lower()
    if value not in WINDOW_ALIASES:
        raise ValueError("Unsupported news window. Use today, past_day, past_week, or past_month.")
    return WINDOW_ALIASES[value]


def _window_start(window: str) -> datetime:
    now = datetime.now(timezone.utc)
    normalized = normalize_news_window(window)
    if normalized == "today":
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if normalized == "past_day":
        return now - timedelta(days=1)
    if normalized == "past_week":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


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
    logger.debug("News provider failed for %s: %s", url, last_error)
    return None


def _parse_dt(value: str | int | float | None) -> datetime:
    if value in (None, ""):
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _canonical_url(url: str | None) -> str:
    if not url:
        return ""
    base = url.strip().lower().split("#", 1)[0]
    return base.split("?", 1)[0]


def _dedupe(items: list[NewsItem], limit: int, *, window: str | None = None) -> list[NewsItem]:
    seen_urls: set[str] = set()
    title_prefixes: set[str] = set()
    unique: list[NewsItem] = []
    tracker = CitationTracker()
    cutoff = _window_start(window) if window else None
    for item in sorted(items, key=lambda row: _parse_dt(row.published_at), reverse=True):
        published = _parse_dt(item.published_at)
        if cutoff and published != datetime.min.replace(tzinfo=timezone.utc) and published < cutoff:
            continue
        url_key = _canonical_url(item.url)
        title_key = unicodedata.normalize("NFKC", item.title).casefold().strip()[:80]
        if url_key and url_key in seen_urls:
            continue
        if title_key and any(title_key.startswith(prefix) or prefix.startswith(title_key) for prefix in title_prefixes):
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            title_prefixes.add(title_key)
        citation = tracker.add(
            "news",
            provider=item.provider or item.source,
            title=item.title,
            url=item.url,
            snippet=item.summary or item.snippet,
            published_at=item.published_at,
            timestamp=item.published_at,
            ticker=(item.tickers_mentioned or item.tickers or [None])[0],
        )
        item.citation_id = f"news-{len(tracker)}"
        item.provider = item.provider or item.source
        item.snippet = item.snippet or item.summary
        item.sentiment_label = item.sentiment_label or item.sentiment or _simple_sentiment(item.title + " " + (item.summary or ""))
        if not item.tickers and item.tickers_mentioned:
            item.tickers = item.tickers_mentioned
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def _simple_sentiment(text: str) -> str:
    lower = text.lower()
    positive = ("beat", "growth", "surge", "record", "raises", "strong", "wins", "profit")
    negative = ("miss", "cuts", "lawsuit", "probe", "falls", "weak", "risk", "warning", "recall")
    score = sum(term in lower for term in positive) - sum(term in lower for term in negative)
    return "bullish" if score > 0 else "bearish" if score < 0 else "neutral"


def _finnhub_company_news(ticker: str, window: str = "past_week") -> list[NewsItem]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []
    end = date.today()
    start = _window_start(window).date()
    data = _get_json(
        "https://finnhub.io/api/v1/company-news",
        {"symbol": ticker.upper(), "from": start.isoformat(), "to": end.isoformat(), "token": api_key},
    )
    if not isinstance(data, list):
        return []
    return [
        NewsItem(
            title=str(item.get("headline") or "Untitled"),
            url=item.get("url"),
            source="Finnhub",
            provider="Finnhub",
            published_at=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc).isoformat() if item.get("datetime") else None,
            summary=item.get("summary"),
            snippet=item.get("summary"),
            tickers_mentioned=[ticker.upper()],
            tickers=[ticker.upper()],
        )
        for item in data
        if item.get("headline")
    ]


def _newsapi_search(query: str, window: str = "past_week") -> list[NewsItem]:
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return []
    data = _get_json(
        "https://newsapi.org/v2/everything",
        {"q": query, "language": "en", "sortBy": "publishedAt", "apiKey": api_key, "from": _window_start(window).date().isoformat(), "domains": "reuters.com,cnbc.com,marketwatch.com,barrons.com,yahoo.com"},
    )
    articles = data.get("articles") if isinstance(data, dict) else []
    return [
        NewsItem(
            title=str(item.get("title") or "Untitled"),
            url=item.get("url"),
            source=(item.get("source") or {}).get("name") or "NewsAPI",
            provider="NewsAPI",
            published_at=item.get("publishedAt"),
            summary=item.get("description"),
            snippet=item.get("description"),
        )
        for item in articles or []
        if item.get("title")
    ]


def _newsdata_search(query: str, window: str = "past_week") -> list[NewsItem]:
    api_key = os.getenv("NEWSDATA_API_KEY")
    if not api_key:
        return []
    data = _get_json(
        "https://newsdata.io/api/1/news",
        {"q": query, "apikey": api_key, "country": "us", "language": "en", "category": "business,technology"},
    )
    results = data.get("results") if isinstance(data, dict) else []
    return [
        NewsItem(
            title=str(item.get("title") or "Untitled"),
            url=item.get("link"),
            source=item.get("source_id") or "NewsData",
            provider="NewsData",
            published_at=item.get("pubDate"),
            summary=item.get("description"),
            snippet=item.get("description"),
        )
        for item in results or []
        if item.get("title")
    ]


def _thenewsapi_search(query: str, window: str = "past_week") -> list[NewsItem]:
    api_key = os.getenv("THENEWSAPI_COM_API_TOKEN") or os.getenv("THENEWSAPI_API_TOKEN")
    if not api_key:
        return []
    data = _get_json(
        "https://api.thenewsapi.com/v1/news/all",
        {"search": query, "api_token": api_key, "locale": "us", "language": "en", "published_after": _window_start(window).date().isoformat()},
    )
    results = data.get("data") if isinstance(data, dict) else []
    return [
        NewsItem(
            title=str(item.get("title") or "Untitled"),
            url=item.get("url"),
            source=item.get("source") or "TheNewsAPI",
            provider="TheNewsAPI",
            published_at=item.get("published_at"),
            summary=item.get("description") or item.get("snippet"),
            snippet=item.get("snippet") or item.get("description"),
        )
        for item in results or []
        if item.get("title")
    ]


def _yfinance_news(ticker: str, limit: int) -> list[NewsItem]:
    try:
        import yfinance as yf

        raw = yf.Ticker(ticker.upper()).get_news(count=limit) or []
    except Exception:
        return []
    items = []
    for article in raw:
        content = article.get("content") if isinstance(article, dict) else None
        if content:
            provider = content.get("provider") or {}
            url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
            items.append(
                NewsItem(
                    title=str(content.get("title") or "Untitled"),
                    url=url_obj.get("url"),
                    source=provider.get("displayName") or "Yahoo Finance",
                    provider="yfinance",
                    published_at=content.get("pubDate"),
                    summary=content.get("summary"),
                    snippet=content.get("summary"),
                    tickers_mentioned=[ticker.upper()],
                    tickers=[ticker.upper()],
                )
            )
        elif article.get("title"):
            items.append(
                NewsItem(
                    title=str(article.get("title")),
                    url=article.get("link"),
                    source=article.get("publisher") or "Yahoo Finance",
                    provider="yfinance",
                    published_at=str(article.get("providerPublishTime")) if article.get("providerPublishTime") else None,
                    summary=article.get("summary"),
                    snippet=article.get("summary"),
                    tickers_mentioned=[ticker.upper()],
                    tickers=[ticker.upper()],
                )
            )
    return items


def search_news(query: str, limit: int = 20, window: str | None = None) -> list[NewsItem]:
    normalized_window = normalize_news_window(window) if window else None
    if demo_provider.is_demo_mode():
        demo_symbol = query.split()[0].upper().replace(".", "-") if query.split() else "SPY"
        if demo_symbol not in demo_provider.demo_universe():
            demo_symbol = "SPY"
        return [NewsItem.model_validate(item) for item in demo_provider.get_demo_news(demo_symbol, limit=limit, window=normalized_window or "today")]
    cache = get_default_cache()
    key = f"search:{query.lower()}:{limit}:{normalized_window or 'all'}"
    cached = cache.get("news", key)
    if cached is not None:
        return [NewsItem.model_validate(item) for item in cached]
    items: list[NewsItem] = []
    for adapter in (_newsapi_search, _newsdata_search, _thenewsapi_search):
        try:
            try:
                items.extend(adapter(query, normalized_window or "past_week"))
            except TypeError:
                items.extend(adapter(query))
        except Exception as exc:
            logger.warning("news_adapter_failed adapter=%s error=%s", adapter.__name__, type(exc).__name__)
    result = _dedupe(items, limit, window=normalized_window)
    cache.set("news", key, [item.model_dump() for item in result], ttl_seconds=NEWS_TTL)
    return result


def get_stock_news(ticker: str, limit: int = 20, window: str = "today") -> list[NewsItem]:
    symbol = ticker.upper().strip()
    window = normalize_news_window(window)
    if demo_provider.is_demo_mode():
        return [NewsItem.model_validate(item) for item in demo_provider.get_demo_news(symbol, limit=limit, window=window)]
    cache = get_default_cache()
    key = f"stock:{symbol}:{limit}:{window}"
    cached = cache.get("news", key)
    if cached is not None:
        return [NewsItem.model_validate(item) for item in cached]
    items: list[NewsItem] = []
    for adapter in (
        lambda query: _finnhub_company_news(query, window),
        lambda query: search_news(f"{query} stock", limit=limit * 2, window=window),
        lambda query: _yfinance_news(query, limit=limit),
    ):
        try:
            items.extend(adapter(symbol))
        except Exception as exc:
            logger.warning("stock_news_adapter_failed ticker=%s error=%s", symbol, type(exc).__name__)
    for item in items:
        if symbol not in item.tickers_mentioned:
            item.tickers_mentioned.append(symbol)
    result = _dedupe(items, limit, window=window)
    cache.set("news", key, [item.model_dump() for item in result], ttl_seconds=NEWS_TTL)
    return result


def get_market_news(limit: int = 30, window: str = "today") -> list[NewsItem]:
    return search_news("US stock market S&P 500 Nasdaq economy", limit=limit, window=window)


def get_earnings_news(ticker: str) -> list[NewsItem]:
    return search_news(f"{ticker.upper()} earnings results guidance EPS revenue", limit=20, window="past_month")

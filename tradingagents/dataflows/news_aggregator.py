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

logger = logging.getLogger(__name__)

NEWS_TTL = 5 * 60


class NewsItem(BaseModel):
    title: str
    url: str | None = None
    source: str
    published_at: str | None = None
    summary: str | None = None
    sentiment: str | None = None
    tickers_mentioned: list[str] = Field(default_factory=list)
    citation_id: str | None = None


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


def _dedupe(items: list[NewsItem], limit: int) -> list[NewsItem]:
    seen_urls: set[str] = set()
    title_prefixes: set[str] = set()
    unique: list[NewsItem] = []
    tracker = CitationTracker()
    for item in sorted(items, key=lambda row: _parse_dt(row.published_at), reverse=True):
        url_key = (item.url or "").strip().lower()
        title_key = unicodedata.normalize("NFKC", item.title).casefold().strip()[:80]
        if url_key and url_key in seen_urls:
            continue
        if title_key and any(title_key.startswith(prefix) or prefix.startswith(title_key) for prefix in title_prefixes):
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            title_prefixes.add(title_key)
        citation = tracker.add("news", title=item.title, url=item.url, snippet=item.summary, timestamp=item.published_at)
        item.citation_id = f"news-{len(tracker)}"
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def _finnhub_company_news(ticker: str) -> list[NewsItem]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return []
    end = date.today()
    start = end - timedelta(days=14)
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
            published_at=datetime.fromtimestamp(item.get("datetime", 0), tz=timezone.utc).isoformat() if item.get("datetime") else None,
            summary=item.get("summary"),
            tickers_mentioned=[ticker.upper()],
        )
        for item in data
        if item.get("headline")
    ]


def _newsapi_search(query: str) -> list[NewsItem]:
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return []
    data = _get_json(
        "https://newsapi.org/v2/everything",
        {"q": query, "language": "en", "sortBy": "publishedAt", "apiKey": api_key, "domains": "reuters.com,cnbc.com,marketwatch.com,barrons.com,yahoo.com"},
    )
    articles = data.get("articles") if isinstance(data, dict) else []
    return [
        NewsItem(
            title=str(item.get("title") or "Untitled"),
            url=item.get("url"),
            source=(item.get("source") or {}).get("name") or "NewsAPI",
            published_at=item.get("publishedAt"),
            summary=item.get("description"),
        )
        for item in articles or []
        if item.get("title")
    ]


def _newsdata_search(query: str) -> list[NewsItem]:
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
            published_at=item.get("pubDate"),
            summary=item.get("description"),
        )
        for item in results or []
        if item.get("title")
    ]


def _thenewsapi_search(query: str) -> list[NewsItem]:
    api_key = os.getenv("THENEWSAPI_COM_API_TOKEN") or os.getenv("THENEWSAPI_API_TOKEN")
    if not api_key:
        return []
    data = _get_json(
        "https://api.thenewsapi.com/v1/news/all",
        {"search": query, "api_token": api_key, "locale": "us", "language": "en"},
    )
    results = data.get("data") if isinstance(data, dict) else []
    return [
        NewsItem(
            title=str(item.get("title") or "Untitled"),
            url=item.get("url"),
            source=item.get("source") or "TheNewsAPI",
            published_at=item.get("published_at"),
            summary=item.get("description") or item.get("snippet"),
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
                    published_at=content.get("pubDate"),
                    summary=content.get("summary"),
                    tickers_mentioned=[ticker.upper()],
                )
            )
        elif article.get("title"):
            items.append(
                NewsItem(
                    title=str(article.get("title")),
                    url=article.get("link"),
                    source=article.get("publisher") or "Yahoo Finance",
                    published_at=str(article.get("providerPublishTime")) if article.get("providerPublishTime") else None,
                    summary=article.get("summary"),
                    tickers_mentioned=[ticker.upper()],
                )
            )
    return items


def search_news(query: str, limit: int = 20) -> list[NewsItem]:
    cache = get_default_cache()
    key = f"search:{query.lower()}:{limit}"
    cached = cache.get("news", key)
    if cached is not None:
        return [NewsItem.model_validate(item) for item in cached]
    items: list[NewsItem] = []
    for adapter in (_newsapi_search, _newsdata_search, _thenewsapi_search):
        try:
            items.extend(adapter(query))
        except Exception as exc:
            logger.warning("news_adapter_failed adapter=%s error=%s", adapter.__name__, type(exc).__name__)
    result = _dedupe(items, limit)
    cache.set("news", key, [item.model_dump() for item in result], ttl_seconds=NEWS_TTL)
    return result


def get_stock_news(ticker: str, limit: int = 20) -> list[NewsItem]:
    symbol = ticker.upper().strip()
    cache = get_default_cache()
    key = f"stock:{symbol}:{limit}"
    cached = cache.get("news", key)
    if cached is not None:
        return [NewsItem.model_validate(item) for item in cached]
    items: list[NewsItem] = []
    for adapter in (
        lambda query: _finnhub_company_news(query),
        lambda query: search_news(f"{query} stock", limit=limit * 2),
        lambda query: _yfinance_news(query, limit=limit),
    ):
        try:
            items.extend(adapter(symbol))
        except Exception as exc:
            logger.warning("stock_news_adapter_failed ticker=%s error=%s", symbol, type(exc).__name__)
    for item in items:
        if symbol not in item.tickers_mentioned:
            item.tickers_mentioned.append(symbol)
    result = _dedupe(items, limit)
    cache.set("news", key, [item.model_dump() for item in result], ttl_seconds=NEWS_TTL)
    return result


def get_market_news(limit: int = 30) -> list[NewsItem]:
    return search_news("US stock market S&P 500 Nasdaq economy", limit=limit)


def get_earnings_news(ticker: str) -> list[NewsItem]:
    return search_news(f"{ticker.upper()} earnings results guidance EPS revenue", limit=20)

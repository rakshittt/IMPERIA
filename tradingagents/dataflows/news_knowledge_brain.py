"""Optional news and web-search vendor aggregation for deep context."""

from __future__ import annotations

import os
from typing import Any

from tradingagents.utils.http import safe_get_json, safe_post_json


def get_newsapi_news(query: str, **kwargs: Any) -> dict[str, Any] | None:
    """Fetch NewsAPI results when an existing free-tier key is present."""

    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return None
    data = safe_get_json(
        "https://newsapi.org/v2/everything",
        params={"q": query, "apiKey": api_key, **kwargs},
        source="newsapi",
    )
    return data if isinstance(data, dict) else None


def get_newsdata_news(query: str, **kwargs: Any) -> dict[str, Any] | None:
    """Fetch NewsData.io results when an existing free-tier key is present."""

    api_key = os.getenv("NEWSDATA_API_KEY")
    if not api_key:
        return None
    data = safe_get_json(
        "https://newsdata.io/api/1/news",
        params={"q": query, "apikey": api_key, **kwargs},
        source="newsdata",
    )
    return data if isinstance(data, dict) else None


def get_thenewsapi_news(query: str, **kwargs: Any) -> dict[str, Any] | None:
    """Fetch TheNewsAPI results when an existing free-tier key is present."""

    api_key = os.getenv("THENEWSAPI_COM_API_TOKEN") or os.getenv("THENEWSAPI_API_TOKEN")
    if not api_key:
        return None
    data = safe_get_json(
        "https://api.thenewsapi.com/v1/news/all",
        params={"search": query, "api_token": api_key, **kwargs},
        source="thenewsapi",
    )
    return data if isinstance(data, dict) else None


def search_tavily(query: str, **kwargs: Any) -> dict[str, Any] | None:
    """Fetch Tavily web search context when an existing free-tier key is present."""

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    data = safe_post_json(
        "https://api.tavily.com/search",
        headers={"Content-Type": "application/json"},
        json_payload={"api_key": api_key, "query": query, "search_depth": "advanced", **kwargs},
        source="tavily",
    )
    return data if isinstance(data, dict) else None


class NewsKnowledgeBrain:
    """Aggregates optional news and web-search vendors for deep research."""

    @staticmethod
    def get_company_news(symbol: str) -> dict[str, Any] | None:
        for source, fetcher in (
            ("NewsAPI", get_newsapi_news),
            ("NewsData", get_newsdata_news),
            ("TheNewsAPI", get_thenewsapi_news),
        ):
            data = fetcher(symbol)
            if data:
                return {"source": source, "data": data}
        return None

    @staticmethod
    def web_search(query: str) -> dict[str, Any] | None:
        data = search_tavily(query)
        return {"source": "Tavily", "data": data} if data else None

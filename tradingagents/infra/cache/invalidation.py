"""Cache invalidation helpers for backend data namespaces."""

from __future__ import annotations

from tradingagents.infra.cache.sqlite import SQLiteCache, get_default_cache


def invalidate_symbol(
    ticker: str,
    namespaces: list[str] | None = None,
    cache: SQLiteCache | None = None,
) -> None:
    """Best-effort invalidation for symbol-scoped cache entries."""

    selected = namespaces or [
        "quotes",
        "profiles",
        "financials",
        "news",
        "ai_summaries",
        "sec_filings",
        "sec_submissions",
        "sec_companyfacts",
    ]
    symbol = ticker.upper().strip()
    backend_cache = cache or get_default_cache()
    for namespace in selected:
        backend_cache.delete(namespace, symbol)


def prune_expired(cache: SQLiteCache | None = None) -> int:
    """Remove expired rows from the default cache."""

    return (cache or get_default_cache()).prune_expired()

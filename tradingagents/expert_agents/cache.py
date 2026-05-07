"""Agent-output cache abstraction for IMPERIA expert-agent graph."""

from __future__ import annotations

import os
from typing import Any

from tradingagents.cache.keys import agent_cache_key
from tradingagents.cache.redis_cache import RedisCache
from tradingagents.cache.sqlite_cache import get_default_cache


class AgentOutputCache:
    """Use Redis in production-style mode and SQLite as local/demo fallback."""

    def __init__(self) -> None:
        self.backend = os.getenv("IMPERIA_CACHE_BACKEND", "sqlite").lower()
        self.redis = RedisCache() if self.backend == "redis" else None
        self.sqlite = get_default_cache()

    def make_key(self, agent_name: str, ticker: str, intent: str, window: str, input_bundle: Any) -> str:
        return agent_cache_key(agent_name, ticker, intent, window, input_bundle)

    def get(self, key: str) -> Any | None:
        if self.redis and self.redis.available:
            return self.redis.get(key)
        return self.sqlite.get("expert_agent_output", key)

    def set(self, key: str, payload: Any, ttl_seconds: int) -> None:
        if self.redis and self.redis.available and self.redis.set(key, payload, ttl_seconds):
            return
        self.sqlite.set("expert_agent_output", key, payload, ttl_seconds=ttl_seconds)


def agent_cache_ttl(agent_name: str) -> int:
    if agent_name in {"price_action"}:
        return 2 * 60
    if agent_name in {"news_event", "sentiment"}:
        return 10 * 60
    if agent_name in {"sec_filings", "insider_activity"}:
        return 24 * 60 * 60
    return 60 * 60

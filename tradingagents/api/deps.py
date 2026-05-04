"""Shared API dependencies."""

from __future__ import annotations

from functools import lru_cache

from tradingagents.engine.fast_query import FastQueryEngine


@lru_cache(maxsize=1)
def get_fast_engine() -> FastQueryEngine:
    return FastQueryEngine()

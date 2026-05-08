"""Shared API dependencies."""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Header, HTTPException


@lru_cache(maxsize=1)
def get_fast_engine():
    from tradingagents.engine.fast_query import FastQueryEngine
    return FastQueryEngine()


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Enforce X-API-Key when IMPERIA_API_KEY env var is set.

    If IMPERIA_API_KEY is not configured the check is skipped so local/demo
    usage works out of the box without credentials.
    """
    configured_key = os.getenv("IMPERIA_API_KEY", "").strip()
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header.")

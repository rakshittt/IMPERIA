"""Optional API response cache middleware for GET JSON endpoints."""

from __future__ import annotations

import hashlib
import json
import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from tradingagents.cache.sqlite_cache import get_default_cache


class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, ttl_seconds: int | None = None):
        super().__init__(app)
        self.ttl_seconds = int(os.getenv("TRADINGAGENTS_API_CACHE_TTL", "15")) if ttl_seconds is None else ttl_seconds
        self.cache = get_default_cache()

    async def dispatch(self, request: Request, call_next):
        if self.ttl_seconds <= 0:
            return await call_next(request)
        if (
            request.method != "GET"
            or not request.url.path.startswith("/api/")
            or request.url.path.endswith("/stream")
            or request.url.path.startswith("/api/research")
            or request.url.path.startswith("/api/watchlist")
            or request.headers.get("authorization")
        ):
            return await call_next(request)
        key = hashlib.sha256(str(request.url).encode("utf-8")).hexdigest()
        cached = self.cache.get("api_response", key)
        if cached is not None:
            return JSONResponse(cached, headers={"X-Cache": "HIT"})

        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body.decode("utf-8"))
            self.cache.set("api_response", key, payload, ttl_seconds=self.ttl_seconds)
        except Exception:
            pass
        headers = dict(response.headers)
        headers["X-Cache"] = "MISS"
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )

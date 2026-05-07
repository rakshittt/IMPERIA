"""Simple in-process API rate limiter."""

from __future__ import annotations

import os
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_requests: int | None = None, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests or int(os.getenv("TRADINGAGENTS_API_RATE_LIMIT", "120"))
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._redis = None
        if os.getenv("IMPERIA_CACHE_BACKEND", "sqlite").lower() == "redis":
            try:
                import redis  # type: ignore

                self._redis = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
                self._redis.ping()
            except Exception:
                self._redis = None

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        if self._redis is not None:
            key = f"rate_limit:{client}"
            member = f"{now}:{uuid.uuid4().hex}"
            cutoff = now - self.window_seconds
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds * 2)
            _removed, _added, count, _expire = pipe.execute()
            if count > self.max_requests:
                retry_after = self.window_seconds
                return JSONResponse(
                    {"error": "rate_limit_exceeded", "detail": "Too many API requests."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            return await call_next(request)
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                return JSONResponse(
                    {"error": "rate_limit_exceeded", "detail": "Too many API requests."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)
        return await call_next(request)

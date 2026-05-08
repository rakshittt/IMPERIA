"""Redis-backed cache/job-state helper with SQLite/local fallback semantics.

Redis is the production-style backend for IMPERIA. The Python package or server
may be absent in local/demo mode, so this module degrades to an unavailable
status instead of breaking deterministic endpoints.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RedisStatus:
    configured: bool
    available: bool
    backend: str
    error: str | None = None


class RedisCache:
    """Tiny Redis JSON cache wrapper used by expert agents and admin health."""

    def __init__(self, url: str | None = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client: Any | None = None
        self._error: str | None = None
        try:
            import redis  # type: ignore

            self._client = redis.Redis.from_url(self.url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            self._client.ping()
        except Exception as exc:
            self._client = None
            self._error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "redis_connection_failed url=%s error=%s -- falling back to SQLite cache",
                self.url,
                self._error,
            )

    @property
    def available(self) -> bool:
        return self._client is not None

    def status(self) -> RedisStatus:
        return RedisStatus(
            configured=bool(os.getenv("REDIS_URL")),
            available=self.available,
            backend=os.getenv("IMPERIA_CACHE_BACKEND", "sqlite"),
            error=self._error,
        )

    def get(self, key: str) -> Any | None:
        if not self._client:
            return None
        value = self._client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        if not self._client:
            return False
        self._client.setex(key, ttl_seconds, json.dumps(value, default=str, separators=(",", ":")))
        return True

    def delete(self, key: str) -> bool:
        if not self._client:
            return False
        self._client.delete(key)
        return True


def redis_status() -> dict[str, Any]:
    return RedisCache().status().__dict__

"""Small failure-safe SQLite cache for market and SEC data.

The cache stores JSON payloads by namespace/key with per-entry TTLs. It is
intentionally conservative: cache failures are logged and treated as misses so
upstream data fetches never fail because the cache is unavailable.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

DEFAULT_TTLS: dict[str, int] = {
    "quotes": 60,
    "indices": 30,
    "profiles": 24 * 60 * 60,
    "financials": 6 * 60 * 60,
    "sec_filings": 60 * 60,
    "sec_submissions": 60 * 60,
    "sec_companyfacts": 6 * 60 * 60,
    "news": 5 * 60,
    "ai_summaries": 15 * 60,
    "search": 24 * 60 * 60,
    "market": 60,
    "market_movers": 120,
    "market_breadth": 5 * 60,
    "sector_performance": 5 * 60,
    "earnings_calendar": 60 * 60,
    "earnings_history": 6 * 60 * 60,
    "screener_metrics": 6 * 60 * 60,
    "polymarket_sentiment": 5 * 60,
    "stock_sentiment": 5 * 60,
    "stock_research": 5 * 60,
    "research_status": 15,
    "api_response": 15,
}


class SQLiteCache:
    """A tiny JSON cache backed by SQLite.

    Parameters:
        db_path: Optional explicit cache path. Defaults to
            ``TRADINGAGENTS_SQLITE_CACHE`` or ``<data_cache_dir>/backend_cache.sqlite3``.
    """

    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        default_path = Path(
            DEFAULT_CONFIG.get("sqlite_cache_path")
            or Path(DEFAULT_CONFIG["data_cache_dir"]) / "backend_cache.sqlite3"
        )
        self.db_path = Path(
            db_path or os.getenv("TRADINGAGENTS_SQLITE_CACHE", str(default_path))
        ).expanduser()
        self._lock = threading.RLock()
        self._ready = False

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        namespace TEXT NOT NULL,
                        cache_key TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        ttl_seconds INTEGER NOT NULL,
                        metadata TEXT,
                        PRIMARY KEY(namespace, cache_key)
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_cache_expiry "
                    "ON cache_entries(namespace, created_at)"
                )
            self._ready = True

    def get(self, namespace: str, key: str) -> Any | None:
        """Return a fresh payload or ``None`` on miss/expiry/failure."""

        row = self._get_row(namespace, key)
        if not row:
            return None
        if self._is_expired(row):
            return None
        return self._decode(row)

    def get_with_metadata(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Return fresh payload plus metadata for callers that need provenance."""

        row = self._get_row(namespace, key)
        if not row or self._is_expired(row):
            return None
        return {
            "payload": self._decode(row),
            "created_at": row["created_at"],
            "ttl_seconds": row["ttl_seconds"],
            "metadata": self._decode_metadata(row),
        }

    def get_stale(self, namespace: str, key: str) -> Any | None:
        """Return payload even if expired. Useful when an upstream is failing."""

        row = self._get_row(namespace, key)
        if not row:
            return None
        return self._decode(row)

    def set(
        self,
        namespace: str,
        key: str,
        payload: Any,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a JSON-serializable payload. Returns ``False`` on cache failure."""

        ttl = int(ttl_seconds or DEFAULT_TTLS.get(namespace, 300))
        try:
            self._ensure_schema()
            encoded = json.dumps(payload, default=str, separators=(",", ":"))
            encoded_metadata = json.dumps(metadata or {}, default=str, separators=(",", ":"))
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO cache_entries(
                        namespace, cache_key, payload, created_at, ttl_seconds, metadata
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(namespace, cache_key) DO UPDATE SET
                        payload=excluded.payload,
                        created_at=excluded.created_at,
                        ttl_seconds=excluded.ttl_seconds,
                        metadata=excluded.metadata
                    """,
                    (namespace, key, encoded, time.time(), ttl, encoded_metadata),
                )
            return True
        except Exception:
            logger.exception("SQLite cache set failed for %s:%s", namespace, key)
            return False

    def delete(self, namespace: str, key: str) -> bool:
        try:
            self._ensure_schema()
            with self._lock, self._connect() as conn:
                conn.execute(
                    "DELETE FROM cache_entries WHERE namespace = ? AND cache_key = ?",
                    (namespace, key),
                )
            return True
        except Exception:
            logger.exception("SQLite cache delete failed for %s:%s", namespace, key)
            return False

    def clear_namespace(self, namespace: str) -> bool:
        try:
            self._ensure_schema()
            with self._lock, self._connect() as conn:
                conn.execute("DELETE FROM cache_entries WHERE namespace = ?", (namespace,))
            return True
        except Exception:
            logger.exception("SQLite cache namespace clear failed for %s", namespace)
            return False

    def prune_expired(self) -> int:
        """Delete expired rows and return the number removed."""

        try:
            self._ensure_schema()
            cutoff = time.time()
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM cache_entries WHERE created_at + ttl_seconds < ?",
                    (cutoff,),
                )
                return int(cur.rowcount or 0)
        except Exception:
            logger.exception("SQLite cache prune failed")
            return 0

    def _get_row(self, namespace: str, key: str) -> sqlite3.Row | None:
        try:
            self._ensure_schema()
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    """
                    SELECT namespace, cache_key, payload, created_at, ttl_seconds, metadata
                    FROM cache_entries
                    WHERE namespace = ? AND cache_key = ?
                    """,
                    (namespace, key),
                )
                return cur.fetchone()
        except Exception:
            logger.exception("SQLite cache get failed for %s:%s", namespace, key)
            return None

    @staticmethod
    def _is_expired(row: sqlite3.Row) -> bool:
        return (float(row["created_at"]) + int(row["ttl_seconds"])) < time.time()

    @staticmethod
    def _decode(row: sqlite3.Row) -> Any | None:
        try:
            return json.loads(row["payload"])
        except Exception:
            logger.exception("SQLite cache payload decode failed")
            return None

    @staticmethod
    def _decode_metadata(row: sqlite3.Row) -> dict[str, Any]:
        try:
            return json.loads(row["metadata"] or "{}")
        except Exception:
            return {}


_DEFAULT_CACHE: SQLiteCache | None = None


def get_default_cache() -> SQLiteCache:
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        _DEFAULT_CACHE = SQLiteCache()
    return _DEFAULT_CACHE

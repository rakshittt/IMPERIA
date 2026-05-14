"""Thread-safe SQLite persistence for watchlists, portfolios, and research jobs."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class PersistenceDB:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        default = Path(".tradingagents_data") / "user_data.db"
        self.path = Path(path or os.getenv("PERSISTENCE_DB_PATH", str(default))).expanduser()
        self._lock = threading.RLock()
        self._ready = False

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            with self.connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watchlists (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        tickers TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                        id TEXT PRIMARY KEY,
                        label TEXT NOT NULL,
                        holdings TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS research_results (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        result_json TEXT,
                        error TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_usage (
                        id TEXT PRIMARY KEY,
                        request_id TEXT,
                        research_id TEXT,
                        model TEXT,
                        agent_name TEXT,
                        ticker TEXT,
                        intent TEXT,
                        mode TEXT,
                        input_tokens INTEGER,
                        output_tokens INTEGER,
                        total_tokens INTEGER,
                        latency_ms INTEGER,
                        success INTEGER,
                        cache_hit INTEGER,
                        error_message TEXT,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_runs (
                        id TEXT PRIMARY KEY,
                        research_id TEXT,
                        agent_name TEXT NOT NULL,
                        ticker TEXT,
                        intent TEXT,
                        mode TEXT,
                        status TEXT NOT NULL,
                        latency_ms INTEGER,
                        cache_hit INTEGER,
                        warnings TEXT,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS admin_errors (
                        id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details TEXT,
                        created_at REAL NOT NULL
                    )
                    """
                )
            self._ready = True

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self.initialize()
        with self._lock, self.connect() as conn:
            conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        self.initialize()
        with self._lock, self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        self.initialize()
        with self._lock, self.connect() as conn:
            return list(conn.execute(sql, params).fetchall())


_DB: PersistenceDB | None = None


def get_persistence_db() -> PersistenceDB:
    global _DB
    if _DB is None:
        _DB = PersistenceDB()
    _DB.initialize()
    return _DB


def dumps(payload: Any) -> str:
    return json.dumps(payload, default=str, separators=(",", ":"))


def loads(payload: str | None, default: Any = None) -> Any:
    if not payload:
        return default
    return json.loads(payload)


def now_ts() -> float:
    return time.time()

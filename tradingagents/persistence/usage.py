"""Persistence helpers for LLM usage, expert-agent runs, and admin error logs."""

from __future__ import annotations

import uuid
from typing import Any

from tradingagents.persistence.db import dumps, get_persistence_db, loads, now_ts


def ensure_usage_tables() -> None:
    db = get_persistence_db()
    db.execute(
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
    db.execute(
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
    db.execute(
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


def record_llm_usage(
    *,
    model: str,
    agent_name: str | None = None,
    ticker: str | None = None,
    intent: str | None = None,
    mode: str | None = None,
    request_id: str | None = None,
    research_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    latency_ms: int | None = None,
    success: bool = True,
    cache_hit: bool = False,
    error_message: str | None = None,
) -> None:
    ensure_usage_tables()
    get_persistence_db().execute(
        """
        INSERT INTO llm_usage(
            id, request_id, research_id, model, agent_name, ticker, intent, mode,
            input_tokens, output_tokens, total_tokens, latency_ms, success, cache_hit,
            error_message, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4())[:12],
            request_id,
            research_id,
            model,
            agent_name,
            ticker,
            intent,
            mode,
            input_tokens,
            output_tokens,
            total_tokens,
            latency_ms,
            1 if success else 0,
            1 if cache_hit else 0,
            error_message,
            now_ts(),
        ),
    )


def list_llm_usage(limit: int = 100) -> list[dict[str, Any]]:
    ensure_usage_tables()
    rows = get_persistence_db().fetchall("SELECT * FROM llm_usage ORDER BY created_at DESC LIMIT ?", (limit,))
    return [dict(row) for row in rows]


def llm_usage_summary() -> dict[str, Any]:
    ensure_usage_tables()
    row = get_persistence_db().fetchone(
        """
        SELECT COUNT(*) AS calls,
               COALESCE(SUM(total_tokens), 0) AS total_tokens,
               COALESCE(SUM(input_tokens), 0) AS input_tokens,
               COALESCE(SUM(output_tokens), 0) AS output_tokens,
               COALESCE(SUM(CASE WHEN success=1 THEN 1 ELSE 0 END), 0) AS successes
        FROM llm_usage
        """
    )
    data = dict(row) if row else {"calls": 0, "total_tokens": 0, "input_tokens": 0, "output_tokens": 0, "successes": 0}
    data["cost_note"] = "Exact DeepSeek pricing is not hardcoded; token usage is exposed for configurable cost estimation."
    return data


def record_agent_run(
    *,
    agent_name: str,
    ticker: str | None,
    intent: str | None,
    mode: str | None,
    status: str,
    latency_ms: int = 0,
    cache_hit: bool = False,
    warnings: list[str] | None = None,
    research_id: str | None = None,
) -> None:
    ensure_usage_tables()
    get_persistence_db().execute(
        """
        INSERT INTO agent_runs(id, research_id, agent_name, ticker, intent, mode, status, latency_ms, cache_hit, warnings, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4())[:12],
            research_id,
            agent_name,
            ticker,
            intent,
            mode,
            status,
            latency_ms,
            1 if cache_hit else 0,
            dumps(warnings or []),
            now_ts(),
        ),
    )


def list_agent_runs(limit: int = 100) -> list[dict[str, Any]]:
    ensure_usage_tables()
    rows = get_persistence_db().fetchall("SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT ?", (limit,))
    result = []
    for row in rows:
        item = dict(row)
        item["warnings"] = loads(item.get("warnings"), [])
        result.append(item)
    return result


def record_error(source: str, message: str, details: dict[str, Any] | None = None) -> None:
    ensure_usage_tables()
    get_persistence_db().execute(
        "INSERT INTO admin_errors(id, source, message, details, created_at) VALUES(?, ?, ?, ?, ?)",
        (str(uuid.uuid4())[:12], source, message, dumps(details or {}), now_ts()),
    )


def list_errors(limit: int = 100) -> list[dict[str, Any]]:
    ensure_usage_tables()
    rows = get_persistence_db().fetchall("SELECT * FROM admin_errors ORDER BY created_at DESC LIMIT ?", (limit,))
    result = []
    for row in rows:
        item = dict(row)
        item["details"] = loads(item.get("details"), {})
        result.append(item)
    return result

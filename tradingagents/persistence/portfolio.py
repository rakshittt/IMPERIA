"""Portfolio snapshots and research result persistence."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.persistence.db import dumps, get_persistence_db, loads, now_ts


class PortfolioRecord(BaseModel):
    id: str
    label: str
    holdings: dict[str, float]
    created_at: float


class ResearchSummary(BaseModel):
    id: str
    status: str
    created_at: float
    updated_at: float
    error: str | None = None


def save_portfolio_snapshot(tickers_with_weights: dict[str, float], label: str) -> PortfolioRecord:
    holdings = {ticker.upper().strip(): float(weight) for ticker, weight in tickers_with_weights.items()}
    record = PortfolioRecord(id=str(uuid.uuid4())[:12], label=label.strip() or "Portfolio", holdings=holdings, created_at=now_ts())
    get_persistence_db().execute(
        "INSERT INTO portfolio_snapshots(id, label, holdings, created_at) VALUES(?, ?, ?, ?)",
        (record.id, record.label, dumps(record.holdings), record.created_at),
    )
    return record


def get_portfolio_snapshot(snapshot_id: str) -> PortfolioRecord:
    row = get_persistence_db().fetchone("SELECT * FROM portfolio_snapshots WHERE id = ?", (snapshot_id,))
    if row is None:
        raise KeyError(f"portfolio snapshot not found: {snapshot_id}")
    return PortfolioRecord(id=row["id"], label=row["label"], holdings=loads(row["holdings"], {}), created_at=row["created_at"])


def list_portfolio_snapshots() -> list[PortfolioRecord]:
    rows = get_persistence_db().fetchall("SELECT * FROM portfolio_snapshots ORDER BY created_at DESC")
    return [PortfolioRecord(id=row["id"], label=row["label"], holdings=loads(row["holdings"], {}), created_at=row["created_at"]) for row in rows]


def delete_portfolio_snapshot(snapshot_id: str) -> bool:
    existing = get_persistence_db().fetchone("SELECT id FROM portfolio_snapshots WHERE id = ?", (snapshot_id,))
    if existing is None:
        raise KeyError(f"portfolio snapshot not found: {snapshot_id}")
    get_persistence_db().execute("DELETE FROM portfolio_snapshots WHERE id = ?", (snapshot_id,))
    return True


def persist_research_result(research_id: str, result_json: dict[str, Any], status: str = "completed", error: str | None = None) -> bool:
    now = now_ts()
    get_persistence_db().execute(
        """
        INSERT INTO research_results(id, status, result_json, error, created_at, updated_at)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            result_json=excluded.result_json,
            error=excluded.error,
            updated_at=excluded.updated_at
        """,
        (research_id, status, dumps(result_json), error, now, now),
    )
    return True


def update_research_status(research_id: str, status: str, result_json: dict[str, Any] | None = None, error: str | None = None) -> bool:
    existing = get_persisted_research(research_id)
    payload = result_json if result_json is not None else (existing.get("result") if existing else None)
    return persist_research_result(research_id, payload or {}, status=status, error=error)


def get_persisted_research(research_id: str) -> dict[str, Any] | None:
    row = get_persistence_db().fetchone("SELECT * FROM research_results WHERE id = ?", (research_id,))
    if row is None:
        return None
    return {
        "id": row["id"],
        "status": row["status"],
        "result": loads(row["result_json"], {}),
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_research_results(limit: int = 20) -> list[ResearchSummary]:
    rows = get_persistence_db().fetchall(
        "SELECT id, status, error, created_at, updated_at FROM research_results ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    return [ResearchSummary(id=row["id"], status=row["status"], error=row["error"], created_at=row["created_at"], updated_at=row["updated_at"]) for row in rows]

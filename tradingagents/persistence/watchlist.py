"""Watchlist CRUD backed by SQLite."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from tradingagents.dataflows.market_data import QuoteData, get_batch_quotes
from tradingagents.persistence.db import dumps, get_persistence_db, loads, now_ts


class WatchlistRecord(BaseModel):
    id: str
    name: str
    tickers: list[str] = Field(default_factory=list)
    created_at: float
    updated_at: float


def _normalize_tickers(tickers: list[str]) -> list[str]:
    result = []
    for ticker in tickers:
        symbol = ticker.upper().strip()
        if symbol and symbol not in result:
            result.append(symbol)
    return result


def _row_to_record(row) -> WatchlistRecord:
    return WatchlistRecord(
        id=row["id"],
        name=row["name"],
        tickers=loads(row["tickers"], []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_watchlist(name: str, tickers: list[str]) -> WatchlistRecord:
    db = get_persistence_db()
    now = now_ts()
    record = WatchlistRecord(
        id=str(uuid.uuid4())[:12],
        name=name.strip() or "Watchlist",
        tickers=_normalize_tickers(tickers),
        created_at=now,
        updated_at=now,
    )
    db.execute(
        "INSERT INTO watchlists(id, name, tickers, created_at, updated_at) VALUES(?, ?, ?, ?, ?)",
        (record.id, record.name, dumps(record.tickers), record.created_at, record.updated_at),
    )
    return record


def get_watchlist(watchlist_id: str) -> WatchlistRecord:
    row = get_persistence_db().fetchone("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))
    if row is None:
        raise KeyError(f"watchlist not found: {watchlist_id}")
    return _row_to_record(row)


def list_watchlists() -> list[WatchlistRecord]:
    rows = get_persistence_db().fetchall("SELECT * FROM watchlists ORDER BY updated_at DESC")
    return [_row_to_record(row) for row in rows]


def _save(record: WatchlistRecord) -> WatchlistRecord:
    record.updated_at = now_ts()
    get_persistence_db().execute(
        "UPDATE watchlists SET name = ?, tickers = ?, updated_at = ? WHERE id = ?",
        (record.name, dumps(record.tickers), record.updated_at, record.id),
    )
    return record


def add_ticker_to_watchlist(watchlist_id: str, ticker: str) -> WatchlistRecord:
    record = get_watchlist(watchlist_id)
    symbol = ticker.upper().strip()
    if symbol and symbol not in record.tickers:
        record.tickers.append(symbol)
    return _save(record)


def remove_ticker_from_watchlist(watchlist_id: str, ticker: str) -> WatchlistRecord:
    record = get_watchlist(watchlist_id)
    symbol = ticker.upper().strip()
    record.tickers = [item for item in record.tickers if item != symbol]
    return _save(record)


def delete_watchlist(watchlist_id: str) -> bool:
    db = get_persistence_db()
    existing = db.fetchone("SELECT id FROM watchlists WHERE id = ?", (watchlist_id,))
    db.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
    return existing is not None


def get_watchlist_quotes(watchlist_id: str) -> list[QuoteData]:
    record = get_watchlist(watchlist_id)
    return list(get_batch_quotes(record.tickers).values())

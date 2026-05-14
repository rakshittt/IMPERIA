from __future__ import annotations

from fastapi import APIRouter, HTTPException

from tradingagents.api.models import WatchlistCreateRequest, WatchlistTickerRequest
from tradingagents.infra.db.watchlist import (
    add_ticker_to_watchlist,
    create_watchlist,
    delete_watchlist,
    get_watchlist,
    get_watchlist_quotes,
    list_watchlists,
    remove_ticker_from_watchlist,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.post("")
async def create(payload: WatchlistCreateRequest):
    return create_watchlist(payload.name, payload.tickers).model_dump()


@router.get("")
async def list_all():
    return [item.model_dump() for item in list_watchlists()]


@router.get("/{watchlist_id}")
async def get_one(watchlist_id: str):
    try:
        return get_watchlist(watchlist_id).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Watchlist not found.")


@router.post("/{watchlist_id}/tickers")
async def add_ticker(watchlist_id: str, payload: WatchlistTickerRequest):
    try:
        return add_ticker_to_watchlist(watchlist_id, payload.ticker).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Watchlist not found.")


@router.delete("/{watchlist_id}/tickers/{ticker}")
async def remove_ticker(watchlist_id: str, ticker: str):
    try:
        return remove_ticker_from_watchlist(watchlist_id, ticker).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail="Watchlist not found.")


@router.delete("/{watchlist_id}")
async def delete(watchlist_id: str):
    return {"deleted": delete_watchlist(watchlist_id)}


@router.get("/{watchlist_id}/quotes")
async def quotes(watchlist_id: str):
    try:
        return [item.model_dump() for item in get_watchlist_quotes(watchlist_id)]
    except KeyError:
        raise HTTPException(status_code=404, detail="Watchlist not found.")

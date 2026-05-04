from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.api.deps import get_fast_engine

router = APIRouter(prefix="/api/market", tags=["market"])
compat_router = APIRouter(tags=["compat"])


@router.get("/indices")
async def indices():
    return get_fast_engine().get_market_indices()


@router.get("/movers")
async def movers(limit: int = Query(10, ge=1, le=25)):
    return get_fast_engine().get_market_movers(limit=limit)


@router.get("/summary")
async def summary():
    return get_fast_engine().get_market_summary()


@compat_router.get("/api/trending")
async def trending_compat():
    movers_data = get_fast_engine().get_market_movers(limit=10)
    return movers_data.get("gainers", []) + movers_data.get("losers", [])


@compat_router.get("/api/market-snapshot")
async def market_snapshot_compat():
    return get_fast_engine().get_market_indices()

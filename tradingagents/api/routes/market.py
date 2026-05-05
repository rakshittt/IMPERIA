from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.dataflows import market_data, news_aggregator

router = APIRouter(prefix="/api/market", tags=["market"])
compat_router = APIRouter(tags=["compat"])


@router.get("/indices")
async def indices():
    return [item.model_dump() for item in market_data.get_market_indices()]


@router.get("/movers")
async def movers(limit: int = Query(10, ge=1, le=25)):
    return market_data.get_market_movers(n=limit).model_dump()


@router.get("/breadth")
async def breadth():
    return market_data.get_market_breadth().model_dump()


@router.get("/sectors")
async def sectors():
    return [item.model_dump() for item in market_data.get_sector_performance()]


@router.get("/summary")
async def summary():
    return {
        "indices": [item.model_dump() for item in market_data.get_market_indices()],
        "movers": market_data.get_market_movers(n=5).model_dump(),
        "breadth": market_data.get_market_breadth().model_dump(),
        "top_news": [item.model_dump() for item in news_aggregator.get_market_news(limit=5)],
    }


@compat_router.get("/api/trending")
async def trending_compat():
    movers_data = market_data.get_market_movers(n=10)
    return [item.model_dump() for item in movers_data.gainers + movers_data.losers]


@compat_router.get("/api/market-snapshot")
async def market_snapshot_compat():
    return [item.model_dump() for item in market_data.get_market_indices()]

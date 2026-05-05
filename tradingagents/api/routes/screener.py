from __future__ import annotations

from fastapi import APIRouter

from tradingagents.api.models import ScreenerNLRequest
from tradingagents.dataflows.screener import ScreenerCriteria, parse_nl_screener_query, screen_stocks

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.post("")
async def screen_compat(request: ScreenerCriteria):
    return await run(request)


@router.post("/run")
async def run(request: ScreenerCriteria):
    return {"criteria": request.model_dump(), "results": [item.model_dump() for item in screen_stocks(request)]}


@router.post("/nl")
async def run_nl(request: ScreenerNLRequest):
    criteria = parse_nl_screener_query(request.query)
    return {
        "query": request.query,
        "criteria": criteria.model_dump(),
        "results": [item.model_dump() for item in screen_stocks(criteria)],
    }

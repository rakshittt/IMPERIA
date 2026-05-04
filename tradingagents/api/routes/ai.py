from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from tradingagents.api.deps import get_fast_engine
from tradingagents.api.models import AskRequest, ResearchRequest
from tradingagents.api.services import (
    RESEARCH_STAGES,
    get_analysis_date,
    research_store,
    run_deep_research,
)
from tradingagents.engine.query_router import route_query

router = APIRouter(prefix="/api", tags=["ai"])


def _holdings_from_tickers(tickers: list[str]) -> list[dict[str, Any]]:
    if not tickers:
        return []
    weight = 1.0 / len(tickers)
    return [{"ticker": ticker, "weight": weight} for ticker in tickers]


@router.post("/ask")
async def ask(payload: AskRequest):
    route = route_query(payload.query)
    if route.mode == "fast":
        return get_fast_engine().answer_query(payload.query)

    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio or []]
    if not portfolio:
        portfolio = _holdings_from_tickers(route.tickers)
    if not portfolio:
        return JSONResponse(
            {
                "mode": "deep",
                "route": route.to_dict(),
                "error": "Deep research requires at least one supported US equity or ETF ticker.",
            },
            status_code=400,
        )
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        run_deep_research,
        portfolio,
        payload.date,
        payload.profile or {},
    )
    return {"mode": "deep", "route": route.to_dict(), "research": result}


@router.post("/research")
async def research(payload: ResearchRequest):
    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio]
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        run_deep_research,
        portfolio,
        payload.date,
        payload.profile or {},
    )
    return result


@router.post("/analyze")
async def analyze_compat(request: Request):
    data = await request.json()
    payload = ResearchRequest(
        portfolio=data.get("portfolio", []),
        date=data.get("date") or datetime.now().strftime("%Y-%m-%d"),
        profile=data.get("profile", {}),
    )
    return await research(payload)


@router.get("/research/{rid}")
async def get_research(rid: str):
    if rid in research_store:
        return research_store[rid]
    return JSONResponse({"error": "Research not found"}, status_code=404)


@router.post("/research/stream")
async def stream_research(request: Request):
    data = await request.json()
    portfolio = data.get("portfolio", [])
    analysis_date = get_analysis_date(data.get("date"))
    user_profile = data.get("profile", {})

    async def event_generator():
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                run_deep_research,
                portfolio,
                analysis_date,
                user_profile,
            )
            for stage in RESEARCH_STAGES:
                yield {"data": json.dumps({"stage": stage, "content": result.get(stage, "")})}
            yield {"data": json.dumps({"stage": "done", "id": result["id"]})}
        except Exception as exc:
            yield {"data": json.dumps({"stage": "error", "message": str(exc)})}

    return EventSourceResponse(event_generator())

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from tradingagents.api.deps import require_api_key
from tradingagents.api.models import ResearchRequest
from tradingagents.api.services import research_store, run_deep_research, run_stock_expert_research
from tradingagents.persistence.portfolio import (
    get_persisted_research,
    list_research_results,
)
from tradingagents.workers.background_jobs import (
    get_research_job,
    research_events,
    research_status_event,
    submit_research_job,
)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("")
async def list_research(limit: int = 20):
    return [item.model_dump() for item in list_research_results(limit=limit)]


@router.post("", dependencies=[Depends(require_api_key)])
async def submit_research(payload: ResearchRequest):
    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio or []]
    if not portfolio and payload.ticker:
        portfolio = [{"ticker": payload.ticker, "weight": 1.0}]
    if not portfolio:
        raise HTTPException(status_code=422, detail="Research requires a ticker or portfolio.")
    profile = payload.profile or {}
    profile.update(
        {
            "ticker": payload.ticker,
            "question": payload.question,
            "window": payload.window,
            "focus": payload.focus,
            "stock_first": bool(payload.ticker and not payload.portfolio),
        }
    )
    runner = run_stock_expert_research if payload.ticker and not payload.portfolio else run_deep_research
    return submit_research_job(runner, portfolio, payload.date, profile)


@router.get("/stream/{research_id}")
async def stream_research_status(research_id: str):
    async def event_generator():
        last = None
        event_index = 0
        for _ in range(240):
            for event in research_events(research_id, event_index):
                event_index += 1
                yield {"event": event.get("event", "status"), "data": json.dumps(event, default=str)}
            payload = research_status_event(research_id)
            if payload != last:
                yield {"event": "status", "data": payload}
                last = payload
            job = get_research_job(research_id)
            if job and job.get("status") in {"completed", "failed"}:
                break
            if job is None:
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.get("/{research_id}/stream")
async def stream_research_status_alias(research_id: str):
    return await stream_research_status(research_id)


@router.post("/stream", dependencies=[Depends(require_api_key)])
async def legacy_stream_research(payload: ResearchRequest):
    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio or []]
    if not portfolio and payload.ticker:
        portfolio = [{"ticker": payload.ticker, "weight": 1.0}]
    submitted = submit_research_job(
        run_stock_expert_research if payload.ticker and not payload.portfolio else run_deep_research,
        portfolio,
        payload.date,
        {**(payload.profile or {}), "ticker": payload.ticker, "question": payload.question, "window": payload.window},
    )
    return await stream_research_status(submitted["research_id"])


@router.get("/{research_id}")
async def get_research(research_id: str):
    persisted = get_persisted_research(research_id)
    if persisted:
        return persisted
    if research_id in research_store:
        return {"id": research_id, "status": "completed", "result": research_store[research_id], "error": None}
    job = get_research_job(research_id)
    if job:
        return job
    raise HTTPException(status_code=404, detail="Research not found.")

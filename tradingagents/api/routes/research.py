from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from tradingagents.api.models import ResearchRequest
from tradingagents.api.services import research_store, run_deep_research
from tradingagents.persistence.portfolio import (
    get_persisted_research,
    list_research_results,
)
from tradingagents.workers.background_jobs import (
    get_research_job,
    research_status_event,
    submit_research_job,
)

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("")
async def list_research(limit: int = 20):
    return [item.model_dump() for item in list_research_results(limit=limit)]


@router.post("")
async def submit_research(payload: ResearchRequest):
    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio]
    return submit_research_job(run_deep_research, portfolio, payload.date, payload.profile or {})


@router.get("/stream/{research_id}")
async def stream_research_status(research_id: str):
    async def event_generator():
        last = None
        for _ in range(240):
            payload = research_status_event(research_id)
            if payload != last:
                yield {"data": payload}
                last = payload
            job = get_research_job(research_id)
            if job and job.get("status") in {"completed", "failed"}:
                break
            if job is None:
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.post("/stream")
async def legacy_stream_research(payload: ResearchRequest):
    submitted = submit_research_job(
        run_deep_research,
        [item.model_dump(exclude_none=True) for item in payload.portfolio],
        payload.date,
        payload.profile or {},
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
    return JSONResponse({"error": "Research not found"}, status_code=404)

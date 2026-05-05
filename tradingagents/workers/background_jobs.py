"""Lightweight in-process background job queue for deep research."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

from tradingagents.persistence.portfolio import (
    get_persisted_research,
    persist_research_result,
    update_research_status,
)

MAX_WORKERS = 3
_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)
_FUTURES: dict[str, Future] = {}


def submit_research_job(
    runner: Callable[[list[dict[str, Any]], str | None, dict[str, Any] | None, str | None], dict[str, Any]],
    portfolio: list[dict[str, Any]],
    analysis_date: str | None,
    profile: dict[str, Any] | None,
    research_id: str | None = None,
) -> dict[str, Any]:
    rid = research_id or str(uuid.uuid4())[:12]
    persist_research_result(rid, {"id": rid, "portfolio": portfolio, "date": analysis_date, "profile": profile or {}}, status="queued")
    future = _EXECUTOR.submit(_run_job, rid, runner, portfolio, analysis_date, profile)
    _FUTURES[rid] = future
    return {"research_id": rid, "id": rid, "status": "queued"}


def _run_job(
    research_id: str,
    runner: Callable[[list[dict[str, Any]], str | None, dict[str, Any] | None, str | None], dict[str, Any]],
    portfolio: list[dict[str, Any]],
    analysis_date: str | None,
    profile: dict[str, Any] | None,
) -> None:
    try:
        update_research_status(research_id, "running")
        result = runner(portfolio, analysis_date, profile or {}, research_id)
        result["id"] = research_id
        update_research_status(research_id, "completed", result_json=result)
    except Exception as exc:
        update_research_status(research_id, "failed", error=str(exc))


def get_research_job(research_id: str) -> dict[str, Any] | None:
    persisted = get_persisted_research(research_id)
    if persisted:
        return persisted
    future = _FUTURES.get(research_id)
    if future is None:
        return None
    status = "completed" if future.done() and not future.exception() else "failed" if future.done() else "running"
    return {"id": research_id, "status": status, "result": {}, "error": str(future.exception()) if future.done() and future.exception() else None}


def research_status_event(research_id: str) -> str:
    payload = get_research_job(research_id) or {"id": research_id, "status": "not_found"}
    return json.dumps(payload, default=str)

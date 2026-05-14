"""Lightweight in-process background job queue for deep research."""

from __future__ import annotations

import json
import logging
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable

from tradingagents.infra.db.portfolio import (
    get_persisted_research,
    persist_research_result,
    update_research_status,
)

MAX_WORKERS = 3
_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)
_FUTURES: dict[str, Future] = {}
_FUTURES_LOCK = RLock()
_EVENTS: dict[str, list[dict[str, Any]]] = {}
_EVENT_LOCK = RLock()
logger = logging.getLogger(__name__)


def emit_research_event(research_id: str, event: str, **payload: Any) -> None:
    row = {"event": event, "research_id": research_id, "timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    with _EVENT_LOCK:
        _EVENTS.setdefault(research_id, []).append(row)
        _EVENTS[research_id] = _EVENTS[research_id][-200:]


def research_events(research_id: str, since: int = 0) -> list[dict[str, Any]]:
    with _EVENT_LOCK:
        return list(_EVENTS.get(research_id, [])[since:])


def submit_research_job(
    runner: Callable[[list[dict[str, Any]], str | None, dict[str, Any] | None, str | None], dict[str, Any]],
    portfolio: list[dict[str, Any]],
    analysis_date: str | None,
    profile: dict[str, Any] | None,
    research_id: str | None = None,
) -> dict[str, Any]:
    rid = research_id or str(uuid.uuid4())[:12]
    persist_research_result(rid, {"id": rid, "portfolio": portfolio, "date": analysis_date, "profile": profile or {}}, status="queued")
    emit_research_event(rid, "queued", warnings=[])
    logger.info("research_job_status job_id=%s status=queued", rid)
    future = _EXECUTOR.submit(_run_job, rid, runner, portfolio, analysis_date, profile)
    with _FUTURES_LOCK:
        _FUTURES[rid] = future
    return {"research_id": rid, "id": rid, "status": "queued"}


def _run_job(
    research_id: str,
    runner: Callable[[list[dict[str, Any]], str | None, dict[str, Any] | None, str | None], dict[str, Any]],
    portfolio: list[dict[str, Any]],
    analysis_date: str | None,
    profile: dict[str, Any] | None,
) -> None:
    started = time.perf_counter()
    try:
        update_research_status(research_id, "running")
        emit_research_event(research_id, "running", warnings=[])
        logger.info("research_job_status job_id=%s status=running", research_id)
        result = runner(portfolio, analysis_date, profile or {}, research_id)
        result["id"] = research_id
        update_research_status(research_id, "completed", result_json=result)
        emit_research_event(research_id, "completed", warnings=result.get("warnings", []) if isinstance(result, dict) else [])
        logger.info(
            "research_job_status job_id=%s status=completed duration_ms=%d",
            research_id,
            int((time.perf_counter() - started) * 1000),
        )
    except Exception as exc:
        update_research_status(research_id, "failed", error=str(exc))
        emit_research_event(research_id, "failed", warnings=[str(exc)])
        logger.warning(
            "research_job_status job_id=%s status=failed duration_ms=%d error=%s",
            research_id,
            int((time.perf_counter() - started) * 1000),
            type(exc).__name__,
        )


def get_research_job(research_id: str) -> dict[str, Any] | None:
    persisted = get_persisted_research(research_id)
    if persisted:
        return persisted
    with _FUTURES_LOCK:
        future = _FUTURES.get(research_id)
    if future is None:
        return None
    status = "completed" if future.done() and not future.exception() else "failed" if future.done() else "running"
    return {"id": research_id, "status": status, "result": {}, "error": str(future.exception()) if future.done() and future.exception() else None}


def research_status_event(research_id: str) -> str:
    payload = get_research_job(research_id) or {"id": research_id, "status": "not_found"}
    return json.dumps(payload, default=str)

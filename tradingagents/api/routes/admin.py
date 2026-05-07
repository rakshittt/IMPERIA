"""Backend-only admin APIs for local/demo observability."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from tradingagents.api.responses import standard_response
from tradingagents.cache.redis_cache import redis_status
from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows.provider_registry import configured_provider_status
from tradingagents.persistence.portfolio import list_research_results
from tradingagents.persistence.usage import list_agent_runs, list_errors, list_llm_usage, llm_usage_summary
from tradingagents.workers.background_jobs import MAX_WORKERS

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _admin_warning() -> list[str]:
    return ["Admin APIs are intended for local/demo backend development; no authentication layer is implemented."]


@router.get("/status")
async def admin_status():
    return standard_response(
        {
            "product": "IMPERIA",
            "admin_api_status": "available",
            "research_streaming_status": "available",
            "thread_pool_max_workers": MAX_WORKERS,
            "cache_backend": os.getenv("IMPERIA_CACHE_BACKEND", "sqlite"),
        },
        warnings=_admin_warning(),
        mode="admin",
        intent="status",
        data_quality="good",
    )


@router.get("/providers")
async def admin_providers():
    return standard_response(configured_provider_status(), warnings=_admin_warning(), mode="admin", intent="providers", data_quality="partial")


@router.get("/cache")
async def admin_cache():
    cache = get_default_cache()
    data: dict[str, Any] = {
        "cache_backend": os.getenv("IMPERIA_CACHE_BACKEND", "sqlite"),
        "sqlite_cache_path": str(cache.db_path),
        "sqlite_cache_exists": Path(cache.db_path).exists(),
        "redis": redis_status(),
    }
    return standard_response(data, warnings=_admin_warning(), mode="admin", intent="cache", data_quality="good")


@router.get("/research-jobs")
async def admin_research_jobs(limit: int = 100):
    return standard_response({"jobs": [item.model_dump() for item in list_research_results(limit=limit)]}, warnings=_admin_warning(), mode="admin", intent="research_jobs", data_quality="good")


@router.get("/agent-runs")
async def admin_agent_runs(limit: int = 100):
    return standard_response({"agent_runs": list_agent_runs(limit=limit)}, warnings=_admin_warning(), mode="admin", intent="agent_runs", data_quality="good")


@router.get("/llm-usage")
async def admin_llm_usage(limit: int = 100):
    return standard_response({"usage": list_llm_usage(limit=limit), "summary": llm_usage_summary()}, warnings=_admin_warning(), mode="admin", intent="llm_usage", data_quality="good")


@router.get("/cost")
async def admin_cost():
    summary = llm_usage_summary()
    summary["cost_dashboard_status"] = "usage_only_no_hardcoded_pricing"
    return standard_response(summary, warnings=_admin_warning(), mode="admin", intent="cost", data_quality="good")


@router.get("/errors")
async def admin_errors(limit: int = 100):
    return standard_response({"errors": list_errors(limit=limit)}, warnings=_admin_warning(), mode="admin", intent="errors", data_quality="good")

"""Helpers for consistent IMPERIA API response envelopes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def standard_response(
    data: dict[str, Any] | None = None,
    *,
    citations: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    mode: str | None = None,
    intent: str | None = None,
    providers_used: list[str] | None = None,
    cache_hit: bool = False,
    data_quality: str = "partial",
    request_id: str | None = None,
) -> dict[str, Any]:
    citation_rows = citations or []
    return {
        "success": True,
        "data": data or {},
        "citations": citation_rows,
        "warnings": warnings or [],
        "metadata": {
            "timestamp": utc_now_iso(),
            "mode": mode,
            "intent": intent,
            "providers_used": providers_used or [],
            "cache_hit": cache_hit,
            "data_quality": data_quality,
            "not_investment_advice": True,
            "citations_available": bool(citation_rows),
            "citation_count": len(citation_rows),
            "request_id": request_id,
        },
    }


def error_response(
    code: str,
    message: str,
    *,
    warnings: list[str] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "warnings": warnings or [],
        "metadata": {
            "timestamp": utc_now_iso(),
            "not_investment_advice": True,
            "citations_available": False,
            "citation_count": 0,
            "request_id": request_id,
        },
    }


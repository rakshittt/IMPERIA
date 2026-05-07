"""FRED macro indicator provider for IMPERIA market-context analysis.

The module is a required backend capability, but FRED itself may be
unconfigured or unavailable. In those cases it returns a structured partial
result with warnings so research can continue using ETF/index proxies.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows.demo_provider import DEMO_SOURCE, DEMO_WARNING, is_demo_mode
from tradingagents.utils.http import safe_get_json

FRED_BASE_URL = os.getenv("FRED_API_BASE", "https://api.stlouisfed.org/fred")
FRED_SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi_yoy": "CPIAUCSL",
    "unemployment": "UNRATE",
    "ten_year_yield": "DGS10",
    "dxy_proxy": "DTWEXBGS",
}


class MacroIndicator(BaseModel):
    name: str
    series_id: str
    value: float | None = None
    observation_date: str | None = None
    source: str = "FRED"


class MacroData(BaseModel):
    provider: str = "FRED"
    indicators: dict[str, MacroIndicator] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _demo_macro() -> MacroData:
    indicators = {
        "fed_funds_rate": MacroIndicator(name="fed_funds_rate", series_id="DEMO_FEDFUNDS", value=4.5, observation_date=datetime.now(timezone.utc).date().isoformat(), source=DEMO_SOURCE),
        "cpi_yoy": MacroIndicator(name="cpi_yoy", series_id="DEMO_CPI", value=3.1, observation_date=datetime.now(timezone.utc).date().isoformat(), source=DEMO_SOURCE),
        "unemployment": MacroIndicator(name="unemployment", series_id="DEMO_UNRATE", value=4.0, observation_date=datetime.now(timezone.utc).date().isoformat(), source=DEMO_SOURCE),
        "ten_year_yield": MacroIndicator(name="ten_year_yield", series_id="DEMO_DGS10", value=4.35, observation_date=datetime.now(timezone.utc).date().isoformat(), source=DEMO_SOURCE),
    }
    return MacroData(
        provider=DEMO_SOURCE,
        indicators=indicators,
        warnings=[DEMO_WARNING],
        citations=[
            {
                "id": "c_demo_fred_macro",
                "source_type": "macro",
                "provider": DEMO_SOURCE,
                "title": "Demo FRED-style macro indicators",
                "url": "https://example.com/imperia-demo/macro",
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    )


def _latest_observation(series_id: str, api_key: str) -> dict[str, Any] | None:
    payload = safe_get_json(
        f"{FRED_BASE_URL.rstrip('/')}/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        },
        source="fred_macro",
        attempts=3,
    )
    observations = payload.get("observations") if isinstance(payload, dict) else None
    return observations[0] if observations else None


def get_macro_indicators() -> MacroData:
    """Return required FRED macro context with graceful degradation."""

    if is_demo_mode():
        return _demo_macro()
    cache = get_default_cache()
    cached = cache.get("fred_macro", "latest")
    if cached is not None:
        return MacroData.model_validate(cached)

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        return MacroData(
            warnings=["FRED_API_KEY is not configured; macro context should fall back to ETF/index proxies."],
            citations=[],
        )

    warnings: list[str] = []
    indicators: dict[str, MacroIndicator] = {}
    citations: list[dict[str, Any]] = []
    for name, series_id in FRED_SERIES.items():
        row = _latest_observation(series_id, api_key)
        if not row:
            warnings.append(f"FRED series {series_id} unavailable.")
            indicators[name] = MacroIndicator(name=name, series_id=series_id)
            continue
        try:
            value = float(row.get("value")) if row.get("value") not in {None, "."} else None
        except (TypeError, ValueError):
            value = None
            warnings.append(f"FRED series {series_id} returned a non-numeric value.")
        indicators[name] = MacroIndicator(name=name, series_id=series_id, value=value, observation_date=row.get("date"))
        citations.append(
            {
                "id": f"c_fred_{series_id.lower()}",
                "source_type": "macro",
                "provider": "FRED",
                "title": f"FRED {series_id}",
                "url": f"https://fred.stlouisfed.org/series/{series_id}",
                "published_at": row.get("date"),
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    result = MacroData(indicators=indicators, warnings=warnings, citations=citations)
    cache.set("fred_macro", "latest", result.model_dump(), ttl_seconds=60 * 60)
    return result

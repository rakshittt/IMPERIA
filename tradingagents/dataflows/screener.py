"""Free-data stock screener with deterministic filters and optional NL parsing."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from tradingagents.cache.sqlite_cache import get_default_cache
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.dataflows.market_data import get_quote, load_universe
from tradingagents.utils.deepseek import deepseek_text

logger = logging.getLogger(__name__)

MAX_UNCACHED_FETCHES = 50


class ScreenerCriteria(BaseModel):
    sectors: list[str] = Field(default_factory=list)
    min_market_cap: float | None = None
    max_market_cap: float | None = None
    min_pe: float | None = None
    max_pe: float | None = None
    min_revenue_growth: float | None = None
    min_gross_margin: float | None = None
    min_net_margin: float | None = None
    min_roe: float | None = None
    max_debt_equity: float | None = None
    min_current_ratio: float | None = None
    exchange: str = "US"
    limit: int = 20

    @field_validator(
        "min_market_cap",
        "max_market_cap",
        "min_pe",
        "max_pe",
        "min_revenue_growth",
        "min_gross_margin",
        "min_net_margin",
        "min_roe",
        "max_debt_equity",
        "min_current_ratio",
    )
    @classmethod
    def numeric_bounds_are_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("Screener numeric bounds must be non-negative.")
        return value

    @field_validator("limit")
    @classmethod
    def limit_is_bounded(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("limit must be between 1 and 100.")
        return value

    @model_validator(mode="after")
    def min_is_below_max(self) -> "ScreenerCriteria":
        pairs = (
            (self.min_market_cap, self.max_market_cap, "market_cap"),
            (self.min_pe, self.max_pe, "pe"),
        )
        for minimum, maximum, name in pairs:
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"min_{name} must be less than or equal to max_{name}.")
        return self

    def has_active_filters(self) -> bool:
        values = self.model_dump(exclude={"exchange", "limit", "sectors"})
        return bool(self.sectors or any(value is not None for value in values.values()))


class ScreenerResult(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None
    market_cap: float | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    score: float = 0
    source: str = "free_screener"
    warnings: list[str] = Field(default_factory=list)


def _number_after(pattern: str, query: str) -> float | None:
    match = re.search(pattern, query, flags=re.I)
    if not match:
        return None
    raw = match.group(1)
    value = float(str(raw).replace("%", ""))
    if "%" in match.group(0):
        value /= 100
    return value


def _deterministic_parse(query: str) -> ScreenerCriteria:
    lower = query.lower()
    sectors = []
    for sector in ["technology", "tech", "financial", "energy", "health", "consumer", "industrial", "utility", "real estate", "materials", "communication"]:
        if sector in lower:
            sectors.append("Technology" if sector == "tech" else sector.title())
    min_net_margin = _number_after(r"net margin\s*(?:over|above|>)\s*(\d+(?:\.\d+)?%?)", query)
    if min_net_margin is None and "profitable" in lower:
        min_net_margin = 0
    criteria = ScreenerCriteria(
        sectors=sectors,
        min_market_cap=_number_after(r"market cap\s*(?:over|above|>)\s*(\d+(?:\.\d+)?)\s*(?:b|bn|billion)", query),
        max_market_cap=_number_after(r"market cap\s*(?:under|below|<)\s*(\d+(?:\.\d+)?)\s*(?:b|bn|billion)", query),
        max_pe=_number_after(r"(?:p/e|pe)\s*(?:under|below|<)\s*(\d+(?:\.\d+)?)", query),
        min_pe=_number_after(r"(?:p/e|pe)\s*(?:over|above|>)\s*(\d+(?:\.\d+)?)", query),
        min_revenue_growth=_number_after(r"revenue growth\s*(?:over|above|>)\s*(\d+(?:\.\d+)?%?)", query),
        min_gross_margin=_number_after(r"gross margin\s*(?:over|above|>)\s*(\d+(?:\.\d+)?%?)", query),
        min_net_margin=min_net_margin,
        min_roe=_number_after(r"roe\s*(?:over|above|>)\s*(\d+(?:\.\d+)?%?)", query),
        max_debt_equity=_number_after(r"debt(?:/| to )equity\s*(?:under|below|<)\s*(\d+(?:\.\d+)?)", query),
        min_current_ratio=_number_after(r"current ratio\s*(?:over|above|>)\s*(\d+(?:\.\d+)?)", query),
        limit=20,
    )
    if criteria.min_market_cap is not None:
        criteria.min_market_cap *= 1_000_000_000
    if criteria.max_market_cap is not None:
        criteria.max_market_cap *= 1_000_000_000
    return criteria


def parse_nl_screener_query(query: str) -> ScreenerCriteria:
    criteria = _deterministic_parse(query)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return criteria
    try:
        content = deepseek_text(
            [
                {"role": "system", "content": "Extract stock screener criteria as compact JSON. Use only keys from ScreenerCriteria."},
                {"role": "user", "content": query},
            ],
            mode="fast",
            temperature=0,
            max_tokens=300,
            timeout=15,
        )
        if not content:
            return criteria
        parsed = json.loads(content[content.find("{") : content.rfind("}") + 1])
        merged = criteria.model_dump()
        for key, value in parsed.items():
            if value not in (None, [], "") and key in merged:
                merged[key] = value
        return ScreenerCriteria.model_validate(merged)
    except Exception:
        return criteria


def _passes(value: float | None, minimum: float | None = None, maximum: float | None = None) -> bool:
    if value is None:
        return False if minimum is not None or maximum is not None else True
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


def _sector_matches(actual_sector: str | None, actual_industry: str | None, requested: list[str]) -> bool:
    if not requested:
        return True
    haystack = f"{actual_sector or ''} {actual_industry or ''}".lower()
    aliases = {
        "tech": "technology",
        "financial": "financial",
        "health": "health",
        "consumer": "consumer",
        "industrial": "industrial",
        "utility": "utilities",
        "communication": "communication",
    }
    for sector in requested:
        needle = aliases.get(sector.lower(), sector.lower())
        if needle in haystack or haystack in needle:
            return True
    return False


def screen_stocks(criteria: ScreenerCriteria) -> list[ScreenerResult]:
    cache = get_default_cache()
    universe = load_universe()
    results: list[ScreenerResult] = []
    uncached = 0
    partial_warning = None
    for ticker in universe:
        metric_key = f"metrics:{ticker}"
        cached = cache.get("screener_metrics", metric_key)
        if cached is None:
            if uncached >= MAX_UNCACHED_FETCHES:
                partial_warning = (
                    f"Partial results: stopped after {MAX_UNCACHED_FETCHES} uncached "
                    "metric fetches to protect free data providers."
                )
                break
            uncached += 1
            try:
                computed = compute_financial_metrics(ticker)
                quote = get_quote(ticker)
                profile = computed.get("profile", {})
                cached = {
                    "ticker": ticker,
                    "name": profile.get("name"),
                    "sector": profile.get("sector"),
                    "industry": profile.get("industry"),
                    "market_cap": quote.market_cap or profile.get("market_cap"),
                    "metrics": computed.get("metrics", {}),
                    "warnings": quote.warnings + computed.get("warnings", []),
                }
                cache.set("screener_metrics", metric_key, cached, ttl_seconds=6 * 60 * 60)
            except Exception as exc:
                cached = {"ticker": ticker, "metrics": {}, "warnings": [str(exc)]}
        metrics = cached.get("metrics", {})
        market_cap = cached.get("market_cap")
        sector = cached.get("sector")
        industry = cached.get("industry")
        if not _sector_matches(sector, industry, criteria.sectors):
            continue
        if not _passes(market_cap, criteria.min_market_cap, criteria.max_market_cap):
            continue
        if not _passes(metrics.get("pe"), criteria.min_pe, criteria.max_pe):
            continue
        if not _passes(metrics.get("revenue_growth"), criteria.min_revenue_growth, None):
            continue
        if not _passes(metrics.get("gross_margin"), criteria.min_gross_margin, None):
            continue
        if not _passes(metrics.get("net_margin"), criteria.min_net_margin, None):
            continue
        if not _passes(metrics.get("roe"), criteria.min_roe, None):
            continue
        if not _passes(metrics.get("debt_to_equity"), None, criteria.max_debt_equity):
            continue
        if not _passes(metrics.get("current_ratio"), criteria.min_current_ratio, None):
            continue
        score = float(market_cap or 0)
        results.append(
            ScreenerResult(
                ticker=ticker,
                name=cached.get("name"),
                sector=sector,
                market_cap=market_cap,
                metrics=metrics,
                score=score,
                warnings=cached.get("warnings", []),
            )
        )
    results.sort(key=lambda item: item.market_cap or 0, reverse=True)
    limited = results[: max(1, min(criteria.limit, 100))]
    if partial_warning and limited:
        limited[0].warnings.append(partial_warning)
    return limited

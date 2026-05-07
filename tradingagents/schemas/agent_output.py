"""Pydantic schemas for IMPERIA expert-agent outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DataFreshness(BaseModel):
    """Freshness metadata for the evidence used by an agent."""

    model_config = ConfigDict(extra="forbid")

    oldest_input_ts: datetime | None = None
    newest_input_ts: datetime | None = None
    stale_data_flag: bool = False


class BaseAgentOutput(BaseModel):
    """Universal contract shared by every IMPERIA expert agent."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    ticker: str
    company_name: str = ""
    task: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence_score: int = Field(default=0, ge=0, le=100)
    citations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    not_investment_advice: Literal[True] = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_freshness: DataFreshness = Field(default_factory=DataFreshness)


class QueryRouterOutput(BaseAgentOutput):
    """Structured deterministic/LLM routing result."""

    intent: Literal[
        "news_summary",
        "why_moving",
        "fundamentals",
        "valuation",
        "sec_filing",
        "earnings",
        "sentiment",
        "bull_bear_thesis",
        "risk_report",
        "compare",
        "deep_research",
        "out_of_scope",
        "simple_lookup",
    ]
    time_window: Literal["intraday", "today", "this_week", "this_month", "this_quarter", "this_year", "long_term", "unspecified"]
    tickers_mentioned: list[str] = Field(default_factory=list)
    mode_recommendation: Literal["fast", "deep"] = "fast"
    rationale: str = ""


class AgentRunRecord(BaseModel):
    """Small execution record used by admin APIs and tests."""

    model_config = ConfigDict(extra="forbid")

    agent_name: str
    ticker: str
    intent: str
    mode: Literal["fast", "deep"]
    status: Literal["completed", "failed", "stub", "cached"]
    latency_ms: int = 0
    cache_hit: bool = False
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceAuditOutput(BaseAgentOutput):
    """Citation and data-quality audit result for a synthesized answer."""

    citation_coverage: float = 0.0
    unsupported_claims: list[str] = Field(default_factory=list)
    fabricated_citation_ids: list[str] = Field(default_factory=list)
    advice_language_violations: list[str] = Field(default_factory=list)
    citation_quality_score: int = Field(default=0, ge=0, le=100)
    data_quality: Literal["excellent", "good", "partial", "poor", "insufficient"] = "partial"
    missing_data: list[str] = Field(default_factory=list)
    stale_data: list[str] = Field(default_factory=list)
    provider_failures: list[str] = Field(default_factory=list)
    confidence_impact: Literal["none", "minor", "moderate", "major"] = "minor"
    recommended_warnings: list[str] = Field(default_factory=list)
    final_answer_safe: bool = True
    recommended_action: Literal["release", "redact_and_release", "reject_and_regenerate"] = "release"


class ExpertGraphResult(BaseModel):
    """Public runtime result for fast and deep expert-agent runs."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    company_name: str = ""
    intent: str
    mode: Literal["fast", "deep"]
    query: str
    time_window: str = "today"
    final_report: dict[str, Any] = Field(default_factory=dict)
    agent_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_quality: Literal["excellent", "good", "partial", "poor", "insufficient"] = "partial"
    providers_used: list[str] = Field(default_factory=list)
    not_investment_advice: Literal[True] = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

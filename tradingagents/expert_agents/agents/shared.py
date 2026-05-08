"""Shared deterministic helpers for IMPERIA expert-agent modules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tradingagents.expert_agents.skill_pack import methodology_for_agent
from tradingagents.schemas.agent_output import BaseAgentOutput, DataFreshness
from tradingagents.utils.confidence import adjust_confidence


def citation_ids(bundle: dict[str, Any], *groups: str) -> list[str]:
    ids: list[str] = []
    citations = bundle.get("citations", [])
    for citation in citations:
        source_type = str(citation.get("source_type") or citation.get("provider") or "").lower()
        if groups and not any(group.lower() in source_type for group in groups):
            continue
        cid = citation.get("id") or citation.get("citation_id")
        if cid and cid not in ids:
            ids.append(str(cid))
    return ids


def freshness_from_bundle(bundle: dict[str, Any]) -> DataFreshness:
    timestamps: list[datetime] = []
    stale = False
    for citation in bundle.get("citations", []):
        raw = citation.get("published_at") or citation.get("timestamp") or citation.get("accessed_at")
        if not raw:
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            timestamps.append(parsed.astimezone(timezone.utc))
        except ValueError:
            pass
    for warning in bundle.get("warnings", []):
        if "stale" in str(warning).lower():
            stale = True
    return DataFreshness(
        oldest_input_ts=min(timestamps) if timestamps else None,
        newest_input_ts=max(timestamps) if timestamps else None,
        stale_data_flag=stale,
    )


def output(
    *,
    agent_name: str,
    bundle: dict[str, Any],
    task: str,
    summary: str,
    key_findings: list[str] | None = None,
    positive: list[str] | None = None,
    negative: list[str] | None = None,
    uncertainties: list[str] | None = None,
    citations: list[str] | None = None,
    warnings: list[str] | None = None,
    confidence: int = 60,
    **custom: Any,
) -> dict[str, Any]:
    freshness = freshness_from_bundle(bundle)
    cite_ids = citations or citation_ids(bundle)
    final_confidence = adjust_confidence(confidence, freshness, len(cite_ids))
    base = BaseAgentOutput(
        agent_name=agent_name,
        ticker=bundle.get("ticker", ""),
        company_name=bundle.get("company_name") or "",
        task=task,
        summary=summary,
        key_findings=key_findings or [],
        positive_signals=positive or [],
        negative_signals=negative or [],
        uncertainties=uncertainties or [],
        confidence_score=final_confidence,
        citations=cite_ids,
        warnings=warnings or [],
        generated_at=datetime.now(timezone.utc),
        data_freshness=freshness,
    ).model_dump(mode="json")
    custom.setdefault("methodology", methodology_for_agent(agent_name))
    base.update(custom)
    return base


def first_cit(bundle: dict[str, Any], fallback: str = "") -> str:
    ids = citation_ids(bundle)
    return ids[0] if ids else fallback

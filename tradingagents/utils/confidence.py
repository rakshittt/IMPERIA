"""Deterministic confidence post-processing for expert-agent outputs."""

from __future__ import annotations

from tradingagents.schemas.agent_output import DataFreshness


def adjust_confidence(raw_score: int, freshness: DataFreshness, citation_count: int) -> int:
    """Cap self-reported confidence using citation coverage and staleness."""

    score = max(0, min(100, int(raw_score)))
    if freshness.stale_data_flag:
        score = min(score, 50)
    if citation_count == 0:
        score = min(score, 25)
    if citation_count == 1:
        score = min(score, 60)
    if score > 85 and citation_count < 3:
        score = 85
    return max(0, min(100, score))

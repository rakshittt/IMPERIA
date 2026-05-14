"""Balanced Thesis Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    upstream = upstream or {}
    positives = []
    negatives = []
    for agent in upstream.values():
        positives.extend(agent.get("positive_signals", [])[:2])
        negatives.extend(agent.get("negative_signals", [])[:2])
    citations = citation_ids(bundle)
    bull = {
        "thesis_summary": "The constructive research case depends on durable fundamentals, improving sentiment, and clean execution in cited data.",
        "supporting_evidence": positives[:5],
        "key_assumptions": ["Growth and margins remain resilient.", "News and earnings catalysts are confirmed by sources."],
        "what_could_break_thesis": ["Deteriorating margins, weaker earnings quality, or adverse filing/news developments."],
    }
    bear = {
        "thesis_summary": "The cautious research case centers on valuation, execution, filing, earnings, or macro risks surfaced by the evidence.",
        "supporting_evidence": negatives[:5],
        "key_assumptions": ["Valuation risk or execution risk remains material.", "Negative catalysts are not offset by fundamentals."],
        "what_could_disprove_bear_case": ["Improving earnings quality, lower valuation risk, or stronger sector/macro backdrop."],
    }
    return output(
        agent_name="Balanced Thesis Agent",
        bundle=bundle,
        task="balanced_thesis",
        summary="Balanced thesis combines bullish and bearish research views without action guidance.",
        key_findings=["Bull and bear views are evidence-based and non-advisory."],
        positive=positives[:5],
        negative=negatives[:5],
        uncertainties=["One-sided evidence lowers confidence in either thesis."],
        citations=citations,
        warnings=[],
        confidence=65 if positives or negatives else 25,
        bull_view=bull,
        bear_view=bear,
        supporting_evidence={"bullish": positives[:5], "bearish": negatives[:5]},
        balanced_takeaway="IMPERIA frames both sides as research factors, not action-oriented advice.",
        scenario_framework={
            "constructive_case": "Requires cited positive evidence to persist and key risks to remain contained.",
            "cautious_case": "Requires cited negative evidence or risk factors to remain material.",
            "base_case": "Mixed or incomplete evidence requires source verification before drawing stronger conclusions.",
        },
    )

"""Risk Analyst Agent."""

from __future__ import annotations

from typing import Any

from .shared import citation_ids, output


def _risk(description: str, category: str, citation_ids_: list[str], severity: str = "medium") -> dict[str, Any]:
    return {"category": category, "description": description, "severity": severity, "time_horizon": "mid", "citation_ids": citation_ids_[:2]}


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    upstream = upstream or {}
    citations = citation_ids(bundle)
    risks = []
    for agent in upstream.values():
        for item in agent.get("negative_signals", [])[:2]:
            risks.append(_risk(str(item), "business", citations))
        for warning in agent.get("warnings", [])[:2]:
            risks.append(_risk(str(warning), "execution", citations, severity="low"))
    if not risks:
        risks = [
            _risk("Free-provider gaps may reduce confidence in the research output.", "execution", citations, "medium"),
            _risk("Valuation, earnings, regulatory, and macro risks should be checked against cited sources.", "valuation", citations, "medium"),
        ]
    summary = f"Risk analysis identified {len(risks)} risk item(s) across available evidence."
    return output(
        agent_name="Risk Analyst",
        bundle=bundle,
        task="risk_analysis",
        summary=summary,
        key_findings=[risk["description"] for risk in risks[:5]],
        negative=[risk["description"] for risk in risks[:5]],
        uncertainties=["Risk taxonomy is limited by upstream data coverage."],
        citations=citations,
        warnings=[],
        confidence=62 if citations else 20,
        business_risks=[risk for risk in risks if risk["category"] == "business"],
        financial_risks=[risk for risk in risks if risk["category"] == "financial"],
        valuation_risks=[risk for risk in risks if risk["category"] == "valuation"],
        regulatory_risks=[risk for risk in risks if risk["category"] == "regulatory"],
        macro_risks=[risk for risk in risks if risk["category"] == "macro"],
        execution_risks=[risk for risk in risks if risk["category"] == "execution"],
        top_3_risks=risks[:3],
        overall_risk_assessment="elevated" if len(risks) >= 4 else "moderate",
    )

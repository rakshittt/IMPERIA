"""Valuation Analyst Agent."""

from __future__ import annotations

from typing import Any

from .shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics_payload = bundle.get("metrics") or {}
    metrics = metrics_payload.get("metrics", {})
    pe = metrics.get("pe")
    forward_pe = metrics.get("forward_pe")
    ev_to_ebitda = metrics.get("ev_to_ebitda")
    revenue_growth = metrics.get("revenue_growth")
    citations = citation_ids(bundle, "financial", "market_data")
    risk = "stretched" if pe and pe > 45 else "elevated" if pe and pe > 30 else "moderate" if pe else "unknown"
    view = "bearish" if risk in {"stretched", "elevated"} and (not revenue_growth or revenue_growth < 0.1) else "neutral" if pe else "mixed"
    summary = f"Valuation context for {bundle.get('ticker')} includes P/E={pe}, forward P/E={forward_pe}, EV/EBITDA={ev_to_ebitda}."
    return output(
        agent_name="Valuation Analyst",
        bundle=bundle,
        task="valuation_analysis",
        summary=summary,
        key_findings=[summary],
        positive=[],
        negative=[f"Valuation risk appears {risk} based on available multiples [cit:{citations[0]}]"] if citations and risk in {"elevated", "stretched"} else [],
        uncertainties=["Historical and peer valuation context may be incomplete."],
        citations=citations,
        warnings=metrics_payload.get("warnings", []),
        confidence=68 if pe or forward_pe else 20,
        valuation_view=view,
        valuation_risk=risk,
        multiple_context={"pe": pe, "forward_pe": forward_pe, "ev_to_ebitda": ev_to_ebitda, "market_cap": metrics_payload.get("market_cap")},
        growth_adjusted_interpretation=f"Revenue growth input is {revenue_growth}; valuation interpretation is limited if growth data is missing.",
        peer_relative_position="unknown",
    )

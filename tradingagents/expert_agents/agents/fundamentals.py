"""Fundamentals Analyst Agent."""

from __future__ import annotations

from typing import Any

from .shared import citation_ids, output


def _direction(value: float | None, positive_threshold: float = 0) -> str:
    if value is None:
        return "mixed"
    return "improving" if value > positive_threshold else "deteriorating" if value < 0 else "stable"


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics_payload = bundle.get("metrics") or {}
    metrics = metrics_payload.get("metrics", {})
    ttm = metrics_payload.get("ttm", {})
    warnings = metrics_payload.get("warnings", [])
    citations = citation_ids(bundle, "financial", "market_data")
    revenue_growth = metrics.get("revenue_growth")
    net_margin = metrics.get("net_margin")
    roe = metrics.get("roe")
    fcf_margin = metrics.get("free_cash_flow_margin")
    positives = []
    negatives = []
    if revenue_growth is not None and revenue_growth > 0:
        positives.append(f"Revenue growth input is positive at {revenue_growth} [cit:{citations[0]}]" if citations else f"Revenue growth input is positive at {revenue_growth}.")
    if net_margin is not None and net_margin <= 0:
        negatives.append(f"Net margin is non-positive at {net_margin} [cit:{citations[0]}]" if citations else f"Net margin is non-positive at {net_margin}.")
    summary = f"Fundamental data covers revenue, margins, returns, leverage, liquidity, and cash flow for {bundle.get('ticker')}."
    return output(
        agent_name="Fundamentals Analyst",
        bundle=bundle,
        task="fundamentals_analysis",
        summary=summary,
        key_findings=[
            f"TTM revenue={ttm.get('revenue')}",
            f"Revenue growth={revenue_growth}",
            f"Net margin={net_margin}",
            f"ROE={roe}",
        ],
        positive=positives,
        negative=negatives,
        uncertainties=[warning for warning in warnings if "Unavailable metric" in warning],
        citations=citations,
        warnings=warnings,
        confidence=74 if metrics else 15,
        growth_view={"direction": _direction(revenue_growth), "summary": f"Revenue growth input: {revenue_growth}."},
        profitability_view={"direction": _direction(net_margin), "summary": f"Net margin input: {net_margin}; ROE input: {roe}."},
        balance_sheet_view={"direction": "mixed", "summary": f"Debt/equity input: {metrics.get('debt_to_equity')}; current ratio input: {metrics.get('current_ratio')}."},
        cash_flow_view={"direction": _direction(fcf_margin), "summary": f"Free cash-flow margin input: {fcf_margin}."},
        fundamental_strengths=positives or ["No strong fundamental strength could be confirmed from available data."],
        fundamental_weaknesses=negatives or ["No severe fundamental weakness could be confirmed from available data."],
        overall_fundamental_view="bullish" if positives and not negatives else "bearish" if negatives and not positives else "mixed",
    )

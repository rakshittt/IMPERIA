"""Insider & Institutional Activity Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    form4 = bundle.get("form4", {})
    institutional = bundle.get("institutional_holders", {})
    thirteen_f = bundle.get("thirteen_f", {})
    transactions = form4.get("transactions", [])
    holders = institutional.get("holders", [])
    citations = citation_ids(bundle, "insider", "institutional", "13f")
    warnings = [
        "Form 4 insider selling may be pre-planned under 10b5-1 plans.",
        "13F data is lagged by nature.",
        "Missing filing data reduces confidence.",
    ]
    warnings.extend(form4.get("warnings", []))
    warnings.extend(thirteen_f.get("warnings", []))
    warnings.extend(institutional.get("warnings", []))
    insider_action = "none"
    if transactions:
        acquired = sum(1 for row in transactions if str(row.get("acquired_disposed")).upper() == "A")
        disposed = sum(1 for row in transactions if str(row.get("acquired_disposed")).upper() == "D")
        insider_action = "net_buying" if acquired > disposed else "net_selling" if disposed > acquired else "balanced"
    summary = f"Insider activity has {len(transactions)} parsed transaction(s); institutional holder table has {len(holders)} holder(s)."
    return output(
        agent_name="Insider & Institutional Activity Agent",
        bundle=bundle,
        task="insider_institutional_activity",
        summary=summary,
        key_findings=[summary],
        uncertainties=warnings[:3],
        citations=citations,
        warnings=warnings,
        confidence=55 if transactions or holders else 15,
        insider_activity_summary=summary,
        insider_net_action=insider_action,
        institutional_activity_summary=f"{len(holders)} institutional holder record(s) available.",
        institutional_net_action=institutional.get("institutional_net_action", "none"),
        signal_strength="moderate" if transactions or holders else "weak",
        interpretation_warnings=warnings[:5],
    )

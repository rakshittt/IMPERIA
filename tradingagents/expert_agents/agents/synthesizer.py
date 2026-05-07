"""Research Synthesizer Agent."""

from __future__ import annotations

from typing import Any

from tradingagents.utils.safety import DISCLAIMER_TEXT, ensure_disclaimer

from .shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    upstream = upstream or {}
    citations = citation_ids(bundle)
    findings: list[str] = []
    positives: list[str] = []
    negatives: list[str] = []
    warnings: list[str] = list(bundle.get("warnings", []))
    for agent_name, result in upstream.items():
        if agent_name == "evidence_auditor":
            continue
        findings.extend(result.get("key_findings", [])[:3])
        positives.extend(result.get("positive_signals", [])[:2])
        negatives.extend(result.get("negative_signals", [])[:2])
        warnings.extend(result.get("warnings", [])[:2])
    ticker = bundle.get("ticker")
    executive = ensure_disclaimer(
        f"{ticker} research summary: IMPERIA gathered market data, news, filings, fundamentals, earnings, sentiment, and context. "
        f"The strongest available findings are: {'; '.join(findings[:3]) or 'data coverage is limited'}."
    )
    final = ensure_disclaimer(
        f"Based on the provided evidence, {ticker} should be researched through price action, recent news, fundamentals, filings, earnings, market context, and risk factors. "
        "This output is source-cited where citations are available and intentionally avoids buy/sell/hold recommendations."
    )
    balanced = upstream.get("balanced_thesis", {})
    factors = upstream.get("research_factors", {})
    report = output(
        agent_name="Research Synthesizer Agent",
        bundle=bundle,
        task="research_synthesis",
        summary=executive,
        key_findings=findings[:7],
        positive=positives[:7],
        negative=negatives[:7],
        uncertainties=warnings[:5],
        citations=citations,
        warnings=sorted({warning for warning in warnings if warning}),
        confidence=68 if citations else 25,
        executive_summary=executive,
        what_happened="; ".join(findings[:5]) or "Available data was too sparse to isolate a driver.",
        why_it_matters="These signals help frame what changed, why it may matter, and which sources should be verified.",
        bullish_factors=positives[:7],
        bearish_factors=negatives[:7],
        balanced_thesis=balanced.get("balanced_takeaway") or "Balanced thesis unavailable or not selected for this intent.",
        bull_view=balanced.get("bull_view"),
        bear_view=balanced.get("bear_view"),
        key_risks=[item.get("description") for item in upstream.get("risk", {}).get("top_3_risks", []) if isinstance(item, dict)],
        what_to_watch_next=["Next earnings", "Recent SEC filings", "News catalysts", "Market/sector context", "Data-quality warnings"],
        factors_to_research=factors.get("what_to_verify_next", ["Verify the cited sources and missing-data warnings."]),
        final_research_summary=final,
        contributing_agents=[name for name in upstream if name != "evidence_auditor"],
        disclaimer=DISCLAIMER_TEXT,
    )
    return report

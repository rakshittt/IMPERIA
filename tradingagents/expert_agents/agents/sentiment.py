"""Market Sentiment Agent."""

from __future__ import annotations

from typing import Any

from .shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    combined = bundle.get("sentiment", {})
    poly = combined.get("signals", {}).get("polymarket") or bundle.get("polymarket") or {}
    analyst = bundle.get("analyst_consensus", {})
    institutional = bundle.get("institutional_holders", {})
    label = combined.get("sentiment_label") or combined.get("research_sentiment") or "uncertain"
    if label not in {"bullish", "bearish", "neutral", "mixed", "uncertain"}:
        label = "uncertain"
    citations = citation_ids(bundle, "news", "prediction_market", "analyst", "institutional", "market_data")
    warnings = list(combined.get("warnings", [])) + list(poly.get("warnings", [])) + list(analyst.get("warnings", [])) + list(institutional.get("warnings", []))
    poly_signals = poly.get("signals", [])
    polymarket_relevance = "none" if not poly_signals else "moderate"
    if not poly_signals and "No sufficiently relevant Polymarket market found for this ticker." not in warnings:
        warnings.append("No sufficiently relevant Polymarket market found for this ticker.")
    summary = f"Research sentiment is {label}; it blends price, news, earnings, sector, analyst consensus, institutional context, and Polymarket signals when available."
    return output(
        agent_name="Market Sentiment Agent",
        bundle=bundle,
        task="market_sentiment_analysis",
        summary=summary,
        key_findings=[summary],
        positive=combined.get("supporting_signals", []) if label == "bullish" else [],
        negative=combined.get("contradicting_signals", []) if label == "bearish" else [],
        uncertainties=warnings[:3],
        citations=citations,
        warnings=warnings,
        confidence=int(combined.get("confidence_score") or 35),
        research_sentiment=label,
        sentiment_label_confidence=int(combined.get("confidence_score") or 0),
        supporting_signals=combined.get("what_solo_investors_should_watch", []),
        contradicting_signals=combined.get("risks", []),
        analyst_consensus_summary=f"buy={analyst.get('buy_count')}, hold={analyst.get('hold_count')}, sell={analyst.get('sell_count')}" if analyst else None,
        polymarket_signals=poly_signals,
        polymarket_relevance=polymarket_relevance,
        institutional_sentiment_context=institutional.get("institutional_net_action"),
    )

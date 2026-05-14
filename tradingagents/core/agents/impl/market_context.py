"""Market Context Analyst Agent."""

from __future__ import annotations

from statistics import mean
from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    macro = bundle.get("macro", {})
    sectors = bundle.get("sectors", [])
    peers = bundle.get("peers", {}).get("peers", [])
    quote = bundle.get("quote", {})
    fred_missing = not macro.get("indicators") or bool(macro.get("warnings"))
    sector_changes = [item.get("change_pct") for item in sectors if item.get("change_pct") is not None]
    sector_avg = mean(sector_changes) if sector_changes else None
    market_regime = "risk-off" if sector_avg is not None and sector_avg < -0.5 else "risk-on" if sector_avg is not None and sector_avg > 0.5 else "mixed"
    citations = citation_ids(bundle, "macro", "market_data", "peer")
    warnings = list(macro.get("warnings", []))
    if fred_missing:
        warnings.append("FRED macro data unavailable; macro context is based on ETF/index proxies only.")
    summary = f"Market context uses FRED indicators when available, sector ETFs, broad indices, VIX, and peer data for {bundle.get('ticker')}."
    return output(
        agent_name="Market Context Analyst",
        bundle=bundle,
        task="market_context_analysis",
        summary=summary,
        key_findings=[f"Sector average change={sector_avg}", f"Ticker change_pct={quote.get('change_pct')}", f"Peer count={len(peers)}"],
        positive=[f"Sector ETF context is positive on average [cit:{citations[0]}]"] if sector_avg and sector_avg > 0.5 and citations else [],
        negative=[f"Sector ETF context is negative on average [cit:{citations[0]}]"] if sector_avg and sector_avg < -0.5 and citations else [],
        uncertainties=["FRED macro indicators unavailable."] if fred_missing else [],
        citations=citations,
        warnings=warnings,
        confidence=62 if sectors or macro.get("indicators") else 25,
        macro_tailwinds=[],
        macro_headwinds=[],
        market_regime=market_regime,
        sector_trend="outperforming" if sector_avg and sector_avg > 0.5 else "underperforming" if sector_avg and sector_avg < -0.5 else "in_line" if sector_avg is not None else "unclear",
        peer_context=f"{len(peers)} peer(s) included in the comparison bundle.",
        stock_specific_vs_sector_move="mixed",
        competitive_position_notes=[f"Peer basket: {', '.join(item.get('ticker', '') for item in peers[:5])}"],
        impact_on_stock="Broad market and sector context can amplify or offset stock-specific news.",
        sector_methodology=[
            "Compare stock movement against broad indices, sector ETFs, VIX context, and peer basket movement.",
            "Treat FRED as the preferred macro source when configured; otherwise disclose ETF/index proxy limits.",
        ],
        competitive_landscape_framework={
            "peer_count": len(peers),
            "sector_etf_count": len(sectors),
            "fred_available": not fred_missing,
        },
    )

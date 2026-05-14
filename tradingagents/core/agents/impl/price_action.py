"""Price Action Analyst Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    quote = bundle.get("quote") or {}
    change = quote.get("change_pct")
    volume = quote.get("volume")
    avg_volume = quote.get("avg_volume")
    rel_volume = (volume / avg_volume) if volume and avg_volume else None
    unusual = bool((change is not None and abs(change) >= 5) or (rel_volume is not None and rel_volume >= 3))
    direction = "up" if (change or 0) > 0 else "down" if (change or 0) < 0 else "flat/unclear"
    summary = f"{bundle.get('ticker')} price action is {direction}; latest change_pct={change}."
    return output(
        agent_name="Price Action Analyst",
        bundle=bundle,
        task="price_action_analysis",
        summary=summary,
        key_findings=[summary, f"Relative volume={rel_volume}" if rel_volume is not None else "Relative volume unavailable"],
        positive=[f"Positive price move of {change}% [cit:{citation_ids(bundle, 'market_data')[0]}]"] if change and change > 0 and citation_ids(bundle, "market_data") else [],
        negative=[f"Negative price move of {change}% [cit:{citation_ids(bundle, 'market_data')[0]}]"] if change and change < 0 and citation_ids(bundle, "market_data") else [],
        uncertainties=[] if change is not None else ["Live price move unavailable."],
        citations=citation_ids(bundle, "market_data"),
        warnings=quote.get("warnings", []),
        confidence=72 if change is not None else 20,
        price_movement_summary=summary,
        volume_context=f"Relative volume is {rel_volume:.2f}x average." if rel_volume else "Average-volume comparison unavailable.",
        relative_market_move=bundle.get("market_context_hint", "SPY/QQQ comparison is included when index data is available."),
        key_level_context=f"52-week range: {quote.get('fifty_two_week_low') or quote.get('52w_low')} to {quote.get('fifty_two_week_high') or quote.get('52w_high')}.",
        unusual_movement_flag=unusual,
        unusual_movement_reason="Large percentage move or elevated relative volume." if unusual else None,
    )

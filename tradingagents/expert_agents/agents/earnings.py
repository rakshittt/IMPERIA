"""Earnings Analyst Agent."""

from __future__ import annotations

from typing import Any

from .shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    earnings = bundle.get("earnings", {})
    history = earnings.get("history", [])
    stats = earnings.get("stats", {})
    next_event = earnings.get("next")
    citations = citation_ids(bundle, "earnings")
    beats = stats.get("beats") or stats.get("beat_count")
    misses = stats.get("misses") or stats.get("miss_count")
    beat_rate = stats.get("beat_rate")
    summary = f"Earnings context includes next_event={bool(next_event)}, history_count={len(history)}, beat_rate={beat_rate}."
    trend = "insufficient_data" if len(history) < 2 else "mixed"
    return output(
        agent_name="Earnings Analyst",
        bundle=bundle,
        task="earnings_analysis",
        summary=summary,
        key_findings=[summary],
        positive=[f"Beat rate is {beat_rate} [cit:{citations[0]}]"] if beat_rate and beat_rate >= 0.6 and citations else [],
        negative=[f"Beat rate is {beat_rate} [cit:{citations[0]}]"] if beat_rate is not None and beat_rate <= 0.35 and citations else [],
        uncertainties=[] if len(history) >= 4 else ["Less than four quarters of earnings history available."],
        citations=citations,
        warnings=earnings.get("warnings", []),
        confidence=70 if len(history) >= 4 else 42 if history else 10,
        next_earnings_context=next_event or {},
        beat_miss_pattern={"beats": beats, "misses": misses, "beat_rate": beat_rate, "history_count": len(history)},
        surprise_trend=trend,
        earnings_quality="Earnings quality requires revenue, EPS, margin, and guidance context; available free data may be partial.",
        guidance_trajectory="unavailable",
        what_to_watch=["EPS versus estimate", "Revenue versus estimate", "Margin commentary", "Guidance tone", "Management discussion of demand"],
        variance_framework={
            "reported_history_count": len(history),
            "beats": beats,
            "misses": misses,
            "estimate_context_available": bool(next_event),
            "guidance_context_available": False,
        },
        pre_earnings_watchlist=[
            "Consensus EPS and revenue versus reported results",
            "Margin and free-cash-flow commentary",
            "Guidance tone and demand commentary",
            "Any one-time items disclosed in the release or filing",
        ],
    )

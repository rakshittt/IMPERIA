"""News & Event Analyst Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    news = bundle.get("news", [])
    if not news:
        return output(
            agent_name="News & Event Analyst",
            bundle=bundle,
            task="news_event_analysis",
            summary="No news articles were available for the selected window.",
            warnings=["no_news_data"],
            confidence=0,
            material_news=[],
            key_events=[],
            catalyst_summary="No catalyst summary available from news.",
            themes=[],
        )
    material = []
    events = []
    positives = []
    negatives = []
    for item in news[:7]:
        title = item.get("title") or "Untitled article"
        sentiment = (item.get("sentiment_label") or item.get("sentiment") or "neutral").lower()
        row = {
            "citation_id": item.get("citation_id") or item.get("id") or "",
            "headline": title,
            "category": item.get("category") or "other",
            "materiality": "high" if len(material) < 3 else "medium",
            "role": "catalyst" if len(material) < 3 else "context",
            "sentiment": sentiment if sentiment in {"bullish", "bearish", "neutral", "mixed"} else "neutral",
        }
        material.append(row)
        events.append(title)
        if row["sentiment"] == "bullish":
            positives.append(f"{title} [cit:{row['citation_id']}]")
        elif row["sentiment"] == "bearish":
            negatives.append(f"{title} [cit:{row['citation_id']}]")
    summary = f"IMPERIA found {len(news)} recent article(s); the most material items are: " + "; ".join(events[:3])
    return output(
        agent_name="News & Event Analyst",
        bundle=bundle,
        task="news_event_analysis",
        summary=summary,
        key_findings=events[:5],
        positive=positives,
        negative=negatives,
        uncertainties=[] if len(news) >= 3 else ["News coverage is sparse for the selected window."],
        citations=citation_ids(bundle, "news"),
        warnings=[] if len(news) >= 3 else ["sparse_news_coverage"],
        confidence=70 if len(news) >= 3 else 38,
        material_news=material,
        key_events=events[:5],
        catalyst_summary="; ".join(events[:3]),
        themes=[item.get("category") or "company-specific news" for item in news[:3]],
    )

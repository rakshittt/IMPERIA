"""Expert-agent registry for the IMPERIA dynamic graph."""

from __future__ import annotations

from .impl import (
    balanced_thesis,
    earnings,
    evidence_auditor,
    fundamentals,
    insider_activity,
    market_context,
    news_event,
    price_action,
    research_factors,
    risk,
    sec_filings,
    sentiment,
    synthesizer,
    valuation,
)

AGENT_FUNCTIONS = {
    "news_event": news_event.run,
    "price_action": price_action.run,
    "fundamentals": fundamentals.run,
    "valuation": valuation.run,
    "sec_filings": sec_filings.run,
    "earnings": earnings.run,
    "market_context": market_context.run,
    "sentiment": sentiment.run,
    "risk": risk.run,
    "balanced_thesis": balanced_thesis.run,
    "insider_activity": insider_activity.run,
    "research_factors": research_factors.run,
    "synthesizer": synthesizer.run,
    "evidence_auditor": evidence_auditor.run,
}

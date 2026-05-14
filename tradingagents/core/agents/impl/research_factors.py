"""Research Factors Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    citations = citation_ids(bundle)
    factors = {
        "valuation_factors_to_research": ["Compare P/E, forward P/E, EV/EBITDA, and growth context against cited inputs."],
        "growth_factors_to_research": ["Review revenue growth, EPS trends, and segment commentary where available."],
        "profitability_factors_to_research": ["Review gross margin, operating margin, net margin, ROE, and ROA."],
        "balance_sheet_factors_to_research": ["Verify debt/equity, liquidity ratios, cash, and refinancing exposure."],
        "earnings_factors_to_research": ["Check next earnings date, EPS estimate, surprise history, and guidance tone."],
        "filing_factors_to_research": ["Read recent 10-K/10-Q/8-K risk factors and MD&A sections where available."],
        "news_factors_to_research": ["Check whether recent headlines are confirmed by official disclosures or earnings data."],
        "risk_factors_to_monitor": ["Monitor valuation, execution, regulatory, macro, and data-quality risks."],
        "what_to_verify_next": ["Open the cited sources and verify any stale or missing fields before relying on the analysis."],
    }
    return output(
        agent_name="Research Factors Agent",
        bundle=bundle,
        task="research_factors",
        summary="Educational research factors are provided without verdict-style scoring or allocation advice.",
        key_findings=factors["what_to_verify_next"],
        citations=citations,
        warnings=[],
        confidence=60 if citations else 20,
        catalyst_calendar_questions=[
            "Which upcoming earnings, filing, product, regulatory, or macro events could change the research picture?",
            "Which cited news events need confirmation from official filings or company disclosures?",
        ],
        disconfirming_evidence_to_track=[
            "Evidence that weakens the constructive scenario.",
            "Evidence that weakens the cautious scenario.",
            "New data that changes valuation, margins, liquidity, earnings quality, or regulatory risk.",
        ],
        **factors,
    )

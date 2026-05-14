"""SEC Filings & Regulatory Analyst Agent."""

from __future__ import annotations

from typing import Any

from ..shared import citation_ids, output


def run(bundle: dict[str, Any], upstream: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    filings = bundle.get("filings", [])
    form4 = bundle.get("form4", {})
    thirteen_f = bundle.get("thirteen_f", {})
    citations = citation_ids(bundle, "sec", "insider", "institutional")
    if not filings:
        return output(
            agent_name="SEC Filings & Regulatory Analyst",
            bundle=bundle,
            task="sec_filings_analysis",
            summary="No recent SEC filing metadata was available.",
            warnings=["no_filings_in_scope"],
            confidence=0,
            filings_analyzed=[],
            filing_summary="No SEC filings available.",
            risk_factor_highlights=[],
            mda_insights=[],
            material_changes=[],
            red_flags=[],
            novelty_vs_prior_filing="unavailable",
        )
    analyzed = [{"citation_id": citations[index] if index < len(citations) else "", "form_type": item.get("filing_type"), "filed_at": item.get("filing_date")} for index, item in enumerate(filings[:5])]
    summary = "Recent SEC filings include: " + "; ".join(f"{item.get('filing_type')} filed {item.get('filing_date')}" for item in filings[:3])
    warnings = []
    warnings.extend(form4.get("warnings", []))
    warnings.extend(thirteen_f.get("warnings", []))
    return output(
        agent_name="SEC Filings & Regulatory Analyst",
        bundle=bundle,
        task="sec_filings_analysis",
        summary=summary,
        key_findings=[summary],
        positive=[],
        negative=[],
        uncertainties=["Risk-factor and MD&A excerpts may be unavailable from free-source metadata."],
        citations=citations,
        warnings=warnings,
        confidence=58 if filings else 0,
        filings_analyzed=analyzed,
        filing_summary=summary,
        risk_factor_highlights=[item.get("summary") or f"Review {item.get('filing_type')} filed {item.get('filing_date')}." for item in filings[:5]],
        mda_insights=[],
        material_changes=[],
        insider_regulatory_notes=form4,
        thirteen_f_notes=thirteen_f,
        red_flags=[],
        novelty_vs_prior_filing="Prior-filing diff unavailable unless extracted filing sections are present.",
    )

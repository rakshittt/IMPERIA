"""Adapted financial-services research methods for IMPERIA expert agents.

This module translates useful workflow patterns from Anthropic's Apache-2.0
financial-services examples into IMPERIA's evidence-first, DeepSeek-only,
non-advisory backend. It intentionally does not vendor external agents,
connectors, or paid-provider assumptions.
"""

from __future__ import annotations

from typing import Any

SKILL_PACK_VERSION = "anthropic-financial-services-adapted-2026-05-07"

SOURCE_ATTRIBUTION: dict[str, str] = {
    "name": "Anthropic financial-services examples",
    "url": "https://github.com/anthropics/financial-services",
    "license": "Apache-2.0",
    "integration_style": "Safe adaptation of research workflows and quality-control patterns; no external runtime dependency.",
}

DISPLAY_NAME_TO_KEY = {
    "News & Event Analyst": "news_event",
    "Price Action Analyst": "price_action",
    "Fundamentals Analyst": "fundamentals",
    "Valuation Analyst": "valuation",
    "SEC Filings & Regulatory Analyst": "sec_filings",
    "Earnings Analyst": "earnings",
    "Market Context Analyst": "market_context",
    "Market Sentiment Agent": "sentiment",
    "Risk Analyst": "risk",
    "Balanced Thesis Agent": "balanced_thesis",
    "Insider & Institutional Activity Agent": "insider_activity",
    "Research Factors Agent": "research_factors",
    "Research Synthesizer Agent": "synthesizer",
    "Evidence & Data Quality Auditor": "evidence_auditor",
}

METHODS_BY_AGENT: dict[str, dict[str, Any]] = {
    "news_event": {
        "label": "event materiality workflow",
        "checks": [
            "Separate confirmed company events from repeated coverage of the same story.",
            "Prioritize source quality, recency, and whether the item explains a cited market move.",
            "Flag untrusted or thinly sourced articles instead of treating them as settled evidence.",
        ],
    },
    "price_action": {
        "label": "market-move diagnostics",
        "checks": [
            "Compare ticker movement against broad indices, sector ETFs, and peer moves.",
            "Separate factual price/volume context from tactical trading language.",
            "Treat unusual volume or gaps as research signals that need corroborating news or filings.",
        ],
    },
    "fundamentals": {
        "label": "financial quality triad",
        "checks": [
            "Review growth, profitability, and cash conversion together before drawing a fundamental view.",
            "Call out balance-sheet and liquidity gaps when inputs are missing or stale.",
            "Use formula metadata and cited source facts for computed ratios.",
        ],
    },
    "valuation": {
        "label": "comps and multiple discipline",
        "checks": [
            "Assess whether multiples are comparable across peer set, history, and growth context.",
            "Flag outliers and missing denominators before interpreting valuation risk.",
            "Avoid target-price language; present valuation as research context only.",
        ],
    },
    "sec_filings": {
        "label": "filing evidence workflow",
        "checks": [
            "Prefer official filings for named risks, MD&A drivers, insider activity, and regulatory events.",
            "Distinguish boilerplate risk language from material or newly emphasized disclosures.",
            "Paraphrase filing excerpts and cite accession-backed records.",
        ],
    },
    "earnings": {
        "label": "earnings variance framework",
        "checks": [
            "Compare reported history, estimates, prior trend, and guidance context when available.",
            "Separate revenue-driven and margin-driven earnings changes when the data supports it.",
            "Frame upcoming earnings as things to monitor, not predictions.",
        ],
    },
    "market_context": {
        "label": "sector and competitive landscape workflow",
        "checks": [
            "Explain whether movement is company-specific, sector-wide, or market-wide.",
            "Use FRED macro data when available and ETF/index proxies when FRED is unavailable.",
            "Map peer and sector context before calling a signal stock-specific.",
        ],
    },
    "sentiment": {
        "label": "multi-signal sentiment triangulation",
        "checks": [
            "Triangulate news tone, analyst consensus, price action, institutional context, and Polymarket signals.",
            "Treat prediction-market signals as weak event-market context unless relevance is strong.",
            "Surface contradictory signals instead of forcing one sentiment label.",
        ],
    },
    "risk": {
        "label": "risk taxonomy and disconfirming evidence",
        "checks": [
            "Classify risks into business, financial, valuation, regulatory, macro, and execution categories.",
            "Look for evidence that would weaken the constructive research case.",
            "Lower confidence when risks are inferred from partial upstream data.",
        ],
    },
    "balanced_thesis": {
        "label": "balanced scenario discipline",
        "checks": [
            "Build constructive and cautious research scenarios from the same evidence bundle.",
            "State assumptions and what evidence would weaken each scenario.",
            "Keep the output balanced and non-prescriptive.",
        ],
    },
    "insider_activity": {
        "label": "ownership-signal caveats",
        "checks": [
            "Separate Form 4 insider activity from lagged 13F institutional data.",
            "Surface pre-planned transaction and 13F lag caveats prominently.",
            "Treat missing ownership data as a confidence reducer, not a reason to invent signal.",
        ],
    },
    "research_factors": {
        "label": "research verification workflow",
        "checks": [
            "Convert evidence into factors to investigate and data points to verify.",
            "Include disconfirming evidence and catalyst questions without verdict-style scoring.",
            "Avoid allocation or action-oriented guidance.",
        ],
    },
    "synthesizer": {
        "label": "source-grounded research note assembly",
        "checks": [
            "Lead with the answer to the user's question, then reconcile conflicting agent outputs.",
            "Do not introduce facts absent from upstream agent JSON.",
            "Keep citations attached to material claims and surface data-quality limits.",
        ],
    },
    "evidence_auditor": {
        "label": "evidence and source-quality audit",
        "checks": [
            "Validate cited IDs against the master registry before release.",
            "Scan for advice language and unsupported named or numeric claims.",
            "Report provider failures, stale data, missing modules, and comparability limits.",
        ],
    },
}


def normalize_agent_key(agent_name: str) -> str:
    """Return the internal agent key for display or registry names."""

    if agent_name in METHODS_BY_AGENT:
        return agent_name
    if agent_name in DISPLAY_NAME_TO_KEY:
        return DISPLAY_NAME_TO_KEY[agent_name]
    return agent_name.lower().replace("&", "and").replace(" ", "_")


def methodology_for_agent(agent_name: str) -> dict[str, Any]:
    """Return safe methodology metadata for an agent output."""

    key = normalize_agent_key(agent_name)
    method = METHODS_BY_AGENT.get(key)
    if not method:
        return {"skill_pack_version": SKILL_PACK_VERSION, "methodology": "general evidence-first research", "checks": []}
    return {
        "skill_pack_version": SKILL_PACK_VERSION,
        "methodology": method["label"],
        "checks": list(method["checks"]),
        "source": SOURCE_ATTRIBUTION["name"],
    }


def agent_method_prompt(agent_name: str) -> str:
    """Return compact prompt text that sharpens DeepSeek agent behavior."""

    method = methodology_for_agent(agent_name)
    checks = "\n".join(f"- {item}" for item in method.get("checks", []))
    return (
        "ADAPTED INSTITUTIONAL RESEARCH METHOD:\n"
        f"Method: {method.get('methodology')}\n"
        f"{checks}\n"
        "Apply these checks only to the provided DATA BUNDLE. Keep the output educational, cited, and non-prescriptive."
    ).strip()


def agent_methods_for_response() -> dict[str, Any]:
    """Return admin/API-friendly skill-pack metadata."""

    return {
        "skill_pack_version": SKILL_PACK_VERSION,
        "source_attribution": SOURCE_ATTRIBUTION,
        "agents": {key: methodology_for_agent(key) for key in METHODS_BY_AGENT},
        "runtime_contract": {
            "agents_fetch_data": False,
            "deepseek_fetches_data": False,
            "data_first": True,
            "investment_advice": False,
        },
    }

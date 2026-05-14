"""Responsible-AI guardrails for educational stock research responses."""

from __future__ import annotations

import re
from dataclasses import dataclass

DISCLAIMER = "Educational research only. Not investment advice."

_DIRECT_ADVICE_PATTERNS = (
    r"\bshould\s+i\s+buy\b",
    r"\bshould\s+i\s+sell\b",
    r"\bshould\s+i\s+hold\b",
    r"\bbuy\s+or\s+sell\b",
    r"\bwhat\s+should\s+i\s+buy\b",
    r"\bwhat\s+should\s+i\s+put\b",
    r"\bput\s+\d+%?\s+.*portfolio\b",
    r"\ballocate\s+\d+%?\b",
)

_FORBIDDEN_OUTPUT_PATTERNS = (
    r"\byou should buy\b",
    r"\byou should sell\b",
    r"\byou should hold\b",
    r"\brecommendation\s*:\s*buy\b",
    r"\brecommendation\s*:\s*sell\b",
    r"\bguaranteed\b",
    r"\brisk-free\b",
)


@dataclass(frozen=True)
class SafetyAssessment:
    requires_reframe: bool
    reason: str | None = None
    disclaimer: str = DISCLAIMER


def assess_query(query: str) -> SafetyAssessment:
    """Detect personalized investment-advice prompts that need reframing."""

    lower = query.lower()
    for pattern in _DIRECT_ADVICE_PATTERNS:
        if re.search(pattern, lower):
            return SafetyAssessment(
                requires_reframe=True,
                reason="The query asks for personalized investment advice or allocation guidance.",
            )
    return SafetyAssessment(requires_reframe=False)


def reframe_prompt(ticker: str | None = None) -> str:
    target = f" {ticker.upper()}" if ticker else ""
    return (
        f"IMPERIA cannot tell you whether to buy, sell, hold, or allocate money to{target}. "
        f"Here are research factors to consider instead: business fundamentals, valuation, "
        f"earnings trajectory, recent SEC filings, news catalysts, market/sector context, "
        f"and key risks. {DISCLAIMER}"
    )


def sanitize_answer(text: str) -> str:
    """Replace accidental direct advice phrasing in generated text."""

    cleaned = text
    replacements = {
        r"\byou should buy\b": "research factors may look constructive for",
        r"\byou should sell\b": "research factors may look concerning for",
        r"\byou should hold\b": "research sentiment appears mixed for",
        r"\brecommendation\s*:\s*buy\b": "research_sentiment: bullish",
        r"\brecommendation\s*:\s*sell\b": "research_sentiment: bearish",
        r"\brisk-free\b": "lower-risk",
        r"\bguaranteed\b": "not guaranteed",
    }
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    if DISCLAIMER.lower() not in cleaned.lower():
        cleaned = f"{cleaned.rstrip()} {DISCLAIMER}"
    return cleaned


def has_direct_advice(text: str) -> bool:
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in _FORBIDDEN_OUTPUT_PATTERNS)


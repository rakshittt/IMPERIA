"""Safety validation shared by IMPERIA APIs, agents, and auditors."""

from __future__ import annotations

import re
from dataclasses import dataclass

DISCLAIMER_TEXT = (
    "IMPERIA is an educational research tool. It is not financial advice, "
    "not an investment recommendation, and not a trading instruction. "
    "Data may be stale or incomplete."
)

FORBIDDEN_PHRASES = [
    r"\byou should (buy|sell|hold)\b",
    r"\bguaranteed\b(?! to fail| not\b)",
    r"\brisk[- ]free\b",
    r"\bput \d+%?\s+of your\b",
    r"\bthis is (financial|investment) advice\b",
    r"\bdefinite prediction\b",
    r"\bwill definitely\b",
    r"\bcertain to (rise|fall|drop|gain)\b",
    r"\bstrong buy\b",
    r"\bstrong sell\b",
]

ALLOWED_SENTIMENT_LABELS = {"bullish", "bearish", "neutral", "mixed", "uncertain"}


@dataclass(frozen=True)
class SafetyResult:
    safe: bool
    violations: list[str]


def find_forbidden_phrases(text: str) -> list[str]:
    """Return forbidden output patterns present in text."""

    hits: list[str] = []
    for pattern in FORBIDDEN_PHRASES:
        if re.search(pattern, text or "", flags=re.IGNORECASE):
            hits.append(pattern)
    return hits


def validate_text_safety(text: str) -> SafetyResult:
    violations = find_forbidden_phrases(text)
    return SafetyResult(safe=not violations, violations=violations)


def validate_sentiment_label(label: str | None) -> bool:
    return (label or "").lower() in ALLOWED_SENTIMENT_LABELS


def ensure_disclaimer(text: str) -> str:
    if DISCLAIMER_TEXT.lower() in (text or "").lower():
        return text
    return f"{(text or '').rstrip()} {DISCLAIMER_TEXT}".strip()

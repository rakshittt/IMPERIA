"""Deterministic-first query routing and agent planning for IMPERIA."""

from __future__ import annotations

import re
from typing import Literal

from tradingagents.schemas.agent_output import QueryRouterOutput
from tradingagents.utils.validation import normalize_ticker

Intent = Literal[
    "news_summary",
    "why_moving",
    "fundamentals",
    "valuation",
    "sec_filing",
    "earnings",
    "sentiment",
    "bull_bear_thesis",
    "risk_report",
    "compare",
    "deep_research",
    "out_of_scope",
    "simple_lookup",
]

INTENT_PATTERNS: dict[str, list[str]] = {
    "simple_lookup": [
        r"\b(what is|show|list)\b.*\b(p/?e|pe ratio|market cap|price|quote|filings?|earnings date)\b",
        r"\bwhen is\b.*\bearnings\b",
    ],
    "news_summary": [r"\b(news|latest|recent|update|coverage)\b", r"\bwhat happened\b"],
    "why_moving": [r"\bwhy\b.*\b(up|down|moving|moved|jumping|dropping|surging|falling)\b", r"\bwhat'?s (driving|causing|behind)\b"],
    "fundamentals": [r"\b(fundamentals|financials|balance sheet|cash flow|profitability|revenue|margins?)\b"],
    "valuation": [r"\b(valuation|expensive|cheap|overvalued|undervalued|p/?e|peg|multiple)\b"],
    "sec_filing": [r"\b(10-?k|10-?q|8-?k|def 14a|proxy|sec filing|annual report|risk factors?)\b"],
    "earnings": [r"\b(earnings|eps|quarter|guidance|beat|miss)\b"],
    "sentiment": [r"\b(sentiment|polymarket|prediction market|market think|mood|consensus)\b"],
    "bull_bear_thesis": [r"\b(bull|bear)\s*(case|thesis|view)\b", r"\bpros and cons\b"],
    "risk_report": [r"\b(risk|risks|risky|dangers?|red flags?)\b"],
    "compare": [r"\b(compare|versus|vs\.?)\b"],
    "deep_research": [r"\b(deep research|full report|comprehensive|long[- ]term|in[- ]depth|expert-level)\b", r"\bsolo investor\b"],
    "out_of_scope": [r"\b(crypto|bitcoin|forex|fx|options strategy|brokerage|place order|trade execution|buy \d+ shares)\b"],
}

FAST_MODE_AGENTS: dict[str, list[str]] = {
    "news_summary": ["news_event", "synthesizer", "evidence_auditor"],
    "why_moving": ["news_event", "price_action", "market_context", "sentiment", "synthesizer", "evidence_auditor"],
    "fundamentals": ["fundamentals", "valuation", "sec_filings", "risk", "synthesizer", "evidence_auditor"],
    "valuation": ["valuation", "fundamentals", "market_context", "synthesizer", "evidence_auditor"],
    "sec_filing": ["sec_filings", "risk", "synthesizer", "evidence_auditor"],
    "earnings": ["earnings", "news_event", "fundamentals", "synthesizer", "evidence_auditor"],
    "sentiment": ["sentiment", "news_event", "price_action", "synthesizer", "evidence_auditor"],
    "risk_report": ["risk", "sec_filings", "news_event", "fundamentals", "valuation", "synthesizer", "evidence_auditor"],
    "bull_bear_thesis": ["fundamentals", "valuation", "news_event", "earnings", "risk", "balanced_thesis", "synthesizer", "evidence_auditor"],
    "simple_lookup": [],
    "default": ["news_event", "fundamentals", "price_action", "synthesizer", "evidence_auditor"],
}

DEEP_MODE_AGENTS: dict[str, list[str]] = {
    "deep_research": [
        "news_event",
        "price_action",
        "fundamentals",
        "valuation",
        "sec_filings",
        "earnings",
        "market_context",
        "sentiment",
        "risk",
        "balanced_thesis",
        "insider_activity",
        "research_factors",
        "synthesizer",
        "evidence_auditor",
    ],
    "compare": ["fundamentals", "valuation", "earnings", "news_event", "market_context", "sentiment", "risk", "synthesizer", "evidence_auditor"],
    "bull_bear_thesis": ["fundamentals", "valuation", "news_event", "earnings", "risk", "market_context", "sentiment", "balanced_thesis", "synthesizer", "evidence_auditor"],
}

NEWS_WINDOW_ALIASES = {
    "today": "today",
    "intraday": "today",
    "past_day": "today",
    "1d": "today",
    "past_week": "this_week",
    "7d": "this_week",
    "week": "this_week",
    "past_month": "this_month",
    "30d": "this_month",
    "month": "this_month",
}


def extract_tickers(query: str) -> list[str]:
    candidates = re.findall(r"\b[A-Z][A-Z0-9.-]{0,5}\b", query or "")
    tickers: list[str] = []
    for candidate in candidates:
        try:
            symbol = normalize_ticker(candidate)
        except ValueError:
            continue
        if symbol not in tickers and symbol not in {"US", "ETF", "SEC", "CEO", "EPS", "P", "E"}:
            tickers.append(symbol)
    return tickers


def normalize_time_window(window: str | None, query: str = "") -> str:
    raw = (window or "").strip().lower()
    if raw:
        return NEWS_WINDOW_ALIASES.get(raw, raw if raw in {"this_week", "this_month", "this_quarter", "this_year", "long_term"} else "today")
    query_l = query.lower()
    if "month" in query_l or "30d" in query_l:
        return "this_month"
    if "week" in query_l or "7d" in query_l:
        return "this_week"
    if "long-term" in query_l or "long term" in query_l:
        return "long_term"
    return "today"


def deterministic_route(query: str) -> str | None:
    matches: list[str] = []
    for intent, patterns in INTENT_PATTERNS.items():
        if any(re.search(pattern, query or "", re.IGNORECASE) for pattern in patterns):
            matches.append(intent)
    if "out_of_scope" in matches:
        return "out_of_scope"
    if "simple_lookup" in matches and re.search(r"\b(what is|show|list|when is)\b", query or "", re.IGNORECASE):
        return "simple_lookup"
    if "deep_research" in matches:
        return "deep_research"
    non_lookup = [intent for intent in matches if intent != "simple_lookup"]
    if len(non_lookup) == 1:
        return non_lookup[0]
    if len(non_lookup) > 1:
        return None
    if matches:
        return matches[0]
    return None


def select_mode(intent: str, explicit_mode: str | None = None) -> Literal["fast", "deep"]:
    if explicit_mode in {"fast", "deep"}:
        return explicit_mode  # type: ignore[return-value]
    return "deep" if intent in {"deep_research", "compare", "risk_report", "bull_bear_thesis"} else "fast"


def plan_query(query: str, *, selected_ticker: str | None = None, window: str | None = None, explicit_mode: str | None = None) -> QueryRouterOutput:
    tickers = [normalize_ticker(selected_ticker)] if selected_ticker else []
    for ticker in extract_tickers(query):
        if ticker not in tickers:
            tickers.append(ticker)
    intent = deterministic_route(query) or "news_summary"
    mode = select_mode(intent, explicit_mode)
    return QueryRouterOutput(
        agent_name="DeterministicQueryRouter",
        ticker=tickers[0] if tickers else "",
        company_name="",
        task="route_query",
        summary=f"Route intent={intent}, mode={mode}.",
        key_findings=[f"intent={intent}", f"mode={mode}"],
        confidence_score=90 if deterministic_route(query) else 55,
        intent=intent,  # type: ignore[arg-type]
        time_window=normalize_time_window(window, query),  # type: ignore[arg-type]
        tickers_mentioned=tickers,
        mode_recommendation=mode,
        rationale="Deterministic pattern route; DeepSeek routing is only needed for ambiguous complex queries.",
    )


def selected_agents_for_intent(intent: str, mode: str) -> list[str]:
    if mode == "deep":
        return DEEP_MODE_AGENTS.get(intent, DEEP_MODE_AGENTS["deep_research"])
    return FAST_MODE_AGENTS.get(intent, FAST_MODE_AGENTS["default"])

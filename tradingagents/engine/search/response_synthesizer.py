"""Cited fast-response synthesis using DeepSeek with deterministic fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from tradingagents.utils.deepseek import deepseek_text

logger = logging.getLogger(__name__)


class SynthesizedAnswer(BaseModel):
    answer_text: str
    key_stats: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.6
    warnings: list[str] = Field(default_factory=list)


def _compact(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump()
    if isinstance(data, list):
        return [_compact(item) for item in data]
    if isinstance(data, dict):
        return {key: _compact(value) for key, value in data.items() if value not in (None, [], {})}
    return data


def _key_stats(bundle: dict[str, Any]) -> dict[str, Any]:
    quote = bundle.get("quote") or {}
    ratios = bundle.get("ratios") or {}
    metrics = ratios.get("metrics") or ratios
    return {
        key: value
        for key, value in {
            "ticker": quote.get("ticker"),
            "price": quote.get("price"),
            "change_pct": quote.get("change_pct"),
            "market_cap": quote.get("market_cap"),
            "pe": metrics.get("pe"),
            "forward_pe": metrics.get("forward_pe"),
            "eps": metrics.get("eps"),
        }.items()
        if value is not None
    }


def _citations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    quote = bundle.get("quote") or {}
    if quote:
        citations.append({"source_type": "market_data", "title": quote.get("source", "Market data"), "url": f"https://finance.yahoo.com/quote/{quote.get('ticker', '')}"})
    if bundle.get("sec_filings") or bundle.get("financials"):
        citations.append({"source_type": "sec", "title": "SEC EDGAR company data", "url": "https://www.sec.gov/edgar/search/"})
    for item in bundle.get("news") or []:
        citations.append({"source_type": "news", "title": item.get("title"), "url": item.get("url"), "timestamp": item.get("published_at")})
    return citations


def _fallback_answer(query: str, bundle: dict[str, Any], warnings: list[str] | None = None) -> SynthesizedAnswer:
    quote = bundle.get("quote") or {}
    profile = bundle.get("profile") or {}
    ratios = bundle.get("ratios") or {}
    metrics = ratios.get("metrics") or ratios
    ticker = quote.get("ticker") or profile.get("ticker") or "the stock"
    name = profile.get("name") or ticker
    parts = [f"{ticker} ({name})"]
    if quote.get("price") is not None:
        parts.append(f"trades around ${quote['price']:,.2f}")
    if quote.get("change_pct") is not None:
        parts.append(f"with a {quote['change_pct']:+.2f}% move")
    if metrics.get("pe") is not None:
        parts.append(f"and a trailing P/E near {metrics['pe']:.2f}")
    if metrics.get("forward_pe") is not None:
        parts.append(f"versus forward P/E near {metrics['forward_pe']:.2f}")
    text = ", ".join(parts) + ". [Source: market data]"
    news = bundle.get("news") or []
    if news:
        text += f" Recent context includes: {news[0].get('title')}. [Source: {news[0].get('source', 'news')}]"
    return SynthesizedAnswer(
        answer_text=text,
        key_stats=_key_stats(bundle),
        citations=_citations(bundle),
        confidence=0.65 if quote else 0.4,
        warnings=warnings or [],
    )


def synthesize_fast_answer(query: str, data_bundle: dict[str, Any]) -> SynthesizedAnswer:
    formatted = json.dumps(_compact(data_bundle), default=str, indent=2)
    system = (
        "You are a financial intelligence assistant answering a question about US stocks. "
        "Use only the data provided. Cite sources inline using [Source: {source_name}]."
    )
    user = f"Question: {query}\n\nData:\n{formatted}\n\nAnswer concisely in 2-4 sentences."
    try:
        text = deepseek_text(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            mode="fast",
            temperature=0.3,
            timeout=15,
        )
        if not text:
            raise ValueError("DeepSeek returned an empty answer")
        return SynthesizedAnswer(
            answer_text=text,
            key_stats=_key_stats(data_bundle),
            citations=_citations(data_bundle),
            confidence=0.82,
        )
    except Exception as exc:
        logger.debug("DeepSeek fast synthesis failed: %s", exc)
        return _fallback_answer(query, data_bundle, [f"DeepSeek synthesis failed: {exc}"])

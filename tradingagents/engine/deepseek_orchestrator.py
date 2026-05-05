"""Context orchestration for DeepSeek fast and deep financial synthesis."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from tradingagents.dataflows import earnings_data, market_data, news_aggregator
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.dataflows.financial_knowledge_brain import FinancialKnowledgeBrain
from tradingagents.dataflows.news_knowledge_brain import NewsKnowledgeBrain
from tradingagents.dataflows.sec_edgar import (
    get_13f_related_filings,
    get_form4_insider_trades,
    get_sec_filings,
    get_xbrl_financials,
)
from tradingagents.utils.validation import normalize_ticker

logger = logging.getLogger(__name__)


def _profile_from_yfinance(ticker: str) -> dict[str, Any]:
    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}
    return {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "source": "yfinance",
    }


class ContextBundle(BaseModel):
    """Structured context gathered from all configured free sources."""

    ticker: str
    query: str
    quote: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    ratios: dict[str, Any] | None = None
    news: list[dict[str, Any]] = Field(default_factory=list)
    next_earnings: dict[str, Any] | None = None
    earnings_history: list[dict[str, Any]] = Field(default_factory=list)
    sec_filings: list[dict[str, Any]] = Field(default_factory=list)
    sec_xbrl: dict[str, Any] | None = None
    insider_trades: list[dict[str, Any]] = Field(default_factory=list)
    institutional_filings: dict[str, Any] | None = None
    market_breadth: dict[str, Any] | None = None
    sector_performance: list[dict[str, Any]] = Field(default_factory=list)
    vendor_context: dict[str, Any] = Field(default_factory=dict)
    web_context: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


async def _call(
    name: str,
    func: Callable[..., Any],
    *args: Any,
    timeout: float = 3,
    **kwargs: Any,
) -> tuple[str, Any, str | None]:
    try:
        result = await asyncio.wait_for(asyncio.to_thread(func, *args, **kwargs), timeout=timeout)
        return name, result, None
    except Exception as exc:
        logger.warning("context_source_failed source=%s error=%s", name, type(exc).__name__)
        return name, None, f"{name} unavailable: {type(exc).__name__}"


class DeepSeekContextOrchestrator:
    """
    Orchestrates data gathering across all free sources to build a rich context
    bundle for DeepSeek synthesis in fast and deep research modes.
    """

    async def build_fast_context(self, ticker: str, query: str) -> ContextBundle:
        """Gather quote, profile, ratios, top news, and next earnings."""

        symbol = normalize_ticker(ticker)
        tasks: list[Awaitable[tuple[str, Any, str | None]]] = [
            _call("quote", market_data.get_quote, symbol, timeout=3),
            _call("profile", _profile_from_yfinance, symbol, timeout=3),
            _call("ratios", compute_financial_metrics, symbol, timeout=3),
            _call("news", news_aggregator.get_stock_news, symbol, 5, timeout=3),
            _call("next_earnings", earnings_data.get_next_earnings, symbol, timeout=3),
        ]
        return self._bundle(symbol, query, await asyncio.gather(*tasks))

    async def build_deep_context(self, ticker: str, query: str) -> ContextBundle:
        """Gather a broad context bundle concurrently with per-source timeouts."""

        symbol = normalize_ticker(ticker)
        tasks: list[Awaitable[tuple[str, Any, str | None]]] = [
            _call("quote", market_data.get_quote, symbol, timeout=5),
            _call("profile", _profile_from_yfinance, symbol, timeout=5),
            _call("ratios", compute_financial_metrics, symbol, timeout=8),
            _call("news", news_aggregator.get_stock_news, symbol, 20, timeout=8),
            _call("next_earnings", earnings_data.get_next_earnings, symbol, timeout=5),
            _call("earnings_history", earnings_data.get_earnings_history, symbol, 8, timeout=8),
            _call("sec_filings", get_sec_filings, symbol, None, 10, timeout=8),
            _call("sec_xbrl", get_xbrl_financials, symbol, timeout=8),
            _call("insider_trades", get_form4_insider_trades, symbol, 25, timeout=8),
            _call("institutional_filings", get_13f_related_filings, symbol, 25, timeout=8),
            _call("market_breadth", market_data.get_market_breadth, timeout=5),
            _call("sector_performance", market_data.get_sector_performance, timeout=5),
            _call("fmp_income", FinancialKnowledgeBrain.get_income_statement, symbol, timeout=8),
            _call("fmp_balance", FinancialKnowledgeBrain.get_balance_sheet, symbol, timeout=8),
            _call("fmp_cashflow", FinancialKnowledgeBrain.get_cashflow, symbol, timeout=8),
            _call("vendor_quote", FinancialKnowledgeBrain.get_stock_data, symbol, timeout=8),
            _call("web_context", NewsKnowledgeBrain.web_search, f"{symbol} stock latest SEC earnings guidance", timeout=8),
        ]
        return self._bundle(symbol, query, await asyncio.gather(*tasks))

    def _bundle(self, symbol: str, query: str, rows: list[tuple[str, Any, str | None]]) -> ContextBundle:
        payload: dict[str, Any] = {"ticker": symbol, "query": query, "vendor_context": {}, "warnings": []}
        for name, value, warning in rows:
            if warning:
                payload["warnings"].append(warning)
            if value is None:
                continue
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            elif isinstance(value, list):
                value = [item.model_dump() if hasattr(item, "model_dump") else item for item in value]
            if name in {"fmp_income", "fmp_balance", "fmp_cashflow", "vendor_quote"}:
                payload["vendor_context"][name] = value
            else:
                payload[name] = value
        return ContextBundle.model_validate(payload)

    def format_for_prompt(self, bundle: ContextBundle) -> str:
        """Format a context bundle into a compact prompt block without null fields."""

        data = bundle.model_dump()
        compact = {key: value for key, value in data.items() if value not in (None, [], {})}
        return json.dumps(compact, default=str, indent=2)[:20000]

"""Fast stock and market query engine backed by free data sources."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from tradingagents.infra.cache.sqlite import DEFAULT_TTLS, SQLiteCache, get_default_cache
import tradingagents.providers.financials.earnings as earnings_data
import tradingagents.providers.market.data as market_data
import tradingagents.providers.news.aggregator as news_aggregator
from tradingagents.providers.financials.metrics import compute_financial_metrics
from tradingagents.providers.market.fallbacks import get_provider_profile_fallback
from tradingagents.providers.filings.edgar import (
    get_13f_related_filings,
    get_form4_insider_trades,
    get_sec_filings,
    get_xbrl_financials,
)
from tradingagents.core.intelligence.citation_tracker import CitationTracker, attach_citations
from tradingagents.core.query.router import route_query
from tradingagents.core.query.synthesizer import synthesize_fast_answer
from tradingagents.core.query.ticker_resolver import resolve_ticker, search_symbols

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        frame = value.copy()
        frame.index = frame.index.map(str)
        frame.columns = frame.columns.map(str)
        return frame.reset_index().to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class FastQueryEngine:
    """Near-instant stock/market answers without running the deep graph."""

    def __init__(self, cache: SQLiteCache | None = None):
        self.cache = cache or get_default_cache()

    def answer_query(self, query: str) -> dict[str, Any]:
        route = route_query(query)
        citations = CitationTracker()
        warnings: list[str] = []
        data: dict[str, Any] = {"route": route.to_dict()}

        try:
            if route.intent == "market_overview" or not route.tickers:
                market = self.get_market_summary()
                data["market"] = market
                answer = self._summarize_market(market)
                citations.add(
                    "market_data",
                    title="Yahoo Finance market index data via yfinance",
                    url="https://finance.yahoo.com/markets/",
                )
            else:
                ticker = route.tickers[0]
                quote = self.get_quote(ticker)
                profile = self.get_profile(ticker)
                ratios = self.get_ratios(ticker)
                news = self.get_news(ticker, limit=5) if route.intent in {"news_query", "earnings", "stock_lookup"} else []
                data.update({"quote": quote, "profile": profile, "ratios": ratios, "news": news})
                synthesized = synthesize_fast_answer(
                    query,
                    {"quote": quote, "profile": profile, "ratios": ratios, "news": news},
                )
                answer = synthesized.answer_text
                warnings.extend(synthesized.warnings)
                citations.extend(synthesized.citations)
                citations.add(
                    "market_data",
                    title=f"Yahoo Finance quote/profile for {ticker} via yfinance",
                    url=f"https://finance.yahoo.com/quote/{ticker}",
                )
                citations.add(
                    "sec",
                    title=f"SEC EDGAR company data for {ticker}",
                    url="https://www.sec.gov/edgar/search/",
                )
                for article in news[:3]:
                    citations.add(
                        "news",
                        title=article.get("title"),
                        url=article.get("url"),
                        snippet=article.get("summary"),
                        timestamp=article.get("published_at") or _now_iso(),
                    )
        except Exception as exc:
            logger.exception("Fast query failed for %r", query)
            answer = f"I could not complete the fast query with free data sources: {exc}"
            warnings.append(str(exc))

        response = {
            "mode": "fast",
            "answer": answer,
            "key_stats": self._key_stats(data),
            "data": data,
            "warnings": warnings,
            "generated_at": _now_iso(),
        }
        return attach_citations(response, citations)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return search_symbols(query, limit=limit)

    def resolve(self, query: str) -> dict[str, Any]:
        return resolve_ticker(query)

    def get_quote(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        cached = self.cache.get("quotes", symbol)
        if cached is not None:
            return cached
        return market_data.get_quote(symbol).model_dump()

    def get_profile(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        cached = self.cache.get("profiles", symbol)
        if cached is not None:
            return cached
        warnings: list[str] = []
        try:
            import yfinance as yf

            info = yf.Ticker(symbol).info or {}
        except Exception as exc:
            info = {}
            warnings.append(f"yfinance profile unavailable: {exc}")
        fallback = get_provider_profile_fallback(symbol) if not info else None
        fallback = fallback or {}
        payload = {
            "ticker": symbol,
            "name": info.get("longName") or info.get("shortName") or fallback.get("name") or symbol,
            "exchange": info.get("exchange") or fallback.get("exchange"),
            "sector": info.get("sector") or fallback.get("sector"),
            "industry": info.get("industry") or fallback.get("industry"),
            "website": info.get("website") or fallback.get("website"),
            "summary": info.get("longBusinessSummary") or fallback.get("summary"),
            "market_cap": info.get("marketCap") or fallback.get("market_cap"),
            "employees": info.get("fullTimeEmployees"),
            "source": "yfinance" if not fallback else fallback.get("source"),
            "warnings": warnings,
        }
        self.cache.set("profiles", symbol, payload, ttl_seconds=DEFAULT_TTLS["profiles"])
        return payload

    def get_financials(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        cached = self.cache.get("financials", symbol)
        if cached is not None:
            return cached
        metrics = compute_financial_metrics(symbol)
        sec_financials: dict[str, Any] | None = None
        try:
            sec_financials = get_xbrl_financials(symbol)
        except Exception as exc:
            metrics.setdefault("warnings", []).append(f"SEC XBRL unavailable: {exc}")
        payload = {"ticker": symbol, "computed": metrics, "sec_xbrl": sec_financials}
        self.cache.set("financials", symbol, payload, ttl_seconds=DEFAULT_TTLS["financials"])
        return payload

    def get_ratios(self, ticker: str) -> dict[str, Any]:
        return self.get_financials(ticker)["computed"]

    def get_news(self, ticker: str, limit: int = 10) -> list[dict[str, Any]]:
        symbol = ticker.upper().strip()
        cache_key = f"{symbol}:{limit}"
        cached = self.cache.get("news", cache_key)
        if cached is not None:
            return cached
        articles = [item.model_dump() for item in news_aggregator.get_stock_news(symbol, limit=limit)]
        self.cache.set("news", cache_key, articles, ttl_seconds=DEFAULT_TTLS["news"])
        return articles

    def get_chart(self, ticker: str, period: str = "1mo", interval: str = "1d") -> dict[str, Any]:
        symbol = ticker.upper().strip()
        cache_key = f"{symbol}:{period}:{interval}"
        cached = self.cache.get("quotes", f"chart:{cache_key}")
        if cached is not None:
            return cached
        history = market_data.get_ohlcv(symbol, period=period, interval=interval)
        payload = {
            "ticker": symbol,
            "period": period,
            "interval": interval,
            "points": market_data.ohlcv_to_records(history),
        }
        self.cache.set("quotes", f"chart:{cache_key}", payload, ttl_seconds=DEFAULT_TTLS["quotes"])
        return payload

    def get_earnings(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        event = earnings_data.get_next_earnings(symbol)
        return {
            "ticker": symbol,
            "history": [item.model_dump() for item in earnings_data.get_earnings_history(symbol)],
            "next": event.model_dump() if event else None,
            "surprise_stats": earnings_data.get_earnings_surprise_stats(symbol).model_dump(),
        }

    def get_holders(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        import yfinance as yf

        stock = yf.Ticker(symbol)
        payload = {
            "ticker": symbol,
            "major_holders": _jsonable(getattr(stock, "major_holders", None)),
            "institutional_holders": _jsonable(getattr(stock, "institutional_holders", None)),
            "mutualfund_holders": _jsonable(getattr(stock, "mutualfund_holders", None)),
            "sec_13f_related": None,
            "source": "yfinance + SEC free filings",
        }
        try:
            payload["sec_13f_related"] = get_13f_related_filings(symbol, limit=25)
        except Exception as exc:
            payload["sec_warning"] = str(exc)
        return payload

    def get_insider_trades(self, ticker: str, limit: int = 50) -> list[dict[str, Any]]:
        return get_form4_insider_trades(ticker, limit=limit)

    def get_filings(self, ticker: str, filing_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return get_sec_filings(ticker, filing_type=filing_type, limit=limit)

    def get_market_indices(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in market_data.get_market_indices()]

    def get_market_movers(self, limit: int = 10) -> dict[str, Any]:
        return market_data.get_market_movers(n=limit).model_dump()

    def get_market_summary(self) -> dict[str, Any]:
        indices = self.get_market_indices()
        movers = self.get_market_movers(limit=5)
        return {
            "indices": indices,
            "movers": movers,
            "breadth": market_data.get_market_breadth().model_dump(),
            "sectors": [item.model_dump() for item in market_data.get_sector_performance()],
            "generated_at": _now_iso(),
        }

    def _summarize_stock(
        self,
        query: str,
        ticker: str,
        quote: dict[str, Any],
        profile: dict[str, Any],
        ratios: dict[str, Any],
        news: list[dict[str, Any]],
    ) -> str:
        price = quote.get("price")
        change_pct = quote.get("change_pct")
        metrics = ratios.get("metrics", {})
        parts = [f"{ticker} ({profile.get('name') or ticker})"]
        if price is not None:
            parts.append(f"last traded around ${price:,.2f}")
        if change_pct is not None:
            parts.append(f"with a {change_pct:+.2f}% move versus the previous close")
        if metrics.get("pe") is not None:
            parts.append(f"trailing P/E is about {metrics['pe']:.2f}")
        if metrics.get("forward_pe") is not None:
            parts.append(f"forward P/E is about {metrics['forward_pe']:.2f}")
        answer = ", ".join(parts) + "."
        if "why" in query.lower() and news:
            headlines = "; ".join(article.get("title") or "" for article in news[:3] if article.get("title"))
            if headlines:
                answer += f" Recent headlines to review: {headlines}."
        return answer

    def _summarize_market(self, market: dict[str, Any]) -> str:
        snippets = []
        for item in market.get("indices", []):
            if item.get("price") is not None and item.get("change_pct") is not None:
                snippets.append(f"{item['name']} {item['change_pct']:+.2f}%")
        if snippets:
            return "Major US indices: " + ", ".join(snippets) + "."
        return "Major US index data is currently unavailable from free sources."

    @staticmethod
    def _key_stats(data: dict[str, Any]) -> dict[str, Any]:
        if "quote" in data:
            metrics = (data.get("ratios") or {}).get("metrics", {})
            return {
                "ticker": data["quote"].get("ticker"),
                "price": data["quote"].get("price"),
                "change_pct": data["quote"].get("change_pct"),
                "market_cap": data["quote"].get("market_cap"),
                "pe": metrics.get("pe"),
                "forward_pe": metrics.get("forward_pe"),
                "eps": metrics.get("eps"),
            }
        return {"indices": data.get("market", {}).get("indices", [])}

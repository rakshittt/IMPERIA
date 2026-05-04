"""Fast stock and market query engine backed by free data sources."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from tradingagents.cache.sqlite_cache import DEFAULT_TTLS, SQLiteCache, get_default_cache
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.dataflows.free_provider_fallbacks import (
    get_provider_profile_fallback,
    get_provider_quote_fallback,
)
from tradingagents.dataflows.sec_edgar import (
    get_13f_related_filings,
    get_form4_insider_trades,
    get_sec_filings,
    get_xbrl_financials,
)
from tradingagents.engine.citation_tracker import CitationTracker, attach_citations
from tradingagents.engine.query_router import route_query
from tradingagents.engine.search.ticker_resolver import resolve_ticker, search_symbols

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


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
                answer = self._summarize_stock(query, ticker, quote, profile, ratios, news)
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
        warnings: list[str] = []
        full_info: dict[str, Any] = {}
        last_price = prev_close = change = change_pct = None
        try:
            import yfinance as yf

            stock = yf.Ticker(symbol)
            info = getattr(stock, "fast_info", None)
            full_info = stock.info or {}
            last_price = _to_float(getattr(info, "last_price", None) if info is not None else None) or _to_float(full_info.get("currentPrice") or full_info.get("regularMarketPrice"))
            prev_close = _to_float(getattr(info, "previous_close", None) if info is not None else None) or _to_float(full_info.get("previousClose"))
            change = (last_price - prev_close) if last_price is not None and prev_close not in (None, 0) else None
            change_pct = (change / prev_close * 100) if change is not None and prev_close else None
        except Exception as exc:
            warnings.append(f"yfinance quote unavailable: {exc}")

        fallback = None
        if last_price is None:
            fallback = get_provider_quote_fallback(symbol)
            if fallback:
                last_price = _to_float(fallback.get("price"))
                prev_close = _to_float(fallback.get("previous_close"))
                change = _to_float(fallback.get("change"))
                change_pct = _to_float(fallback.get("change_pct"))
            else:
                stale = self.cache.get_stale("quotes", symbol)
                if stale is not None:
                    stale.setdefault("warnings", []).append("Returned stale cached quote after live providers failed.")
                    return stale
        payload = {
            "ticker": symbol,
            "name": full_info.get("shortName") or full_info.get("longName") or symbol,
            "exchange": full_info.get("exchange") or (fallback or {}).get("exchange"),
            "price": last_price,
            "previous_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "open": full_info.get("open") or (fallback or {}).get("open"),
            "day_high": full_info.get("dayHigh") or (fallback or {}).get("day_high"),
            "day_low": full_info.get("dayLow") or (fallback or {}).get("day_low"),
            "volume": full_info.get("volume") or (fallback or {}).get("volume"),
            "market_cap": full_info.get("marketCap"),
            "as_of": _now_iso(),
            "source": "yfinance" if fallback is None else fallback.get("source"),
            "warnings": warnings,
        }
        self.cache.set("quotes", symbol, payload, ttl_seconds=DEFAULT_TTLS["quotes"])
        return payload

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
        import yfinance as yf

        stock = yf.Ticker(symbol)
        raw_news = stock.get_news(count=limit) or []
        articles: list[dict[str, Any]] = []
        for item in raw_news[:limit]:
            content = item.get("content") if isinstance(item, dict) else None
            if content:
                provider = content.get("provider") or {}
                url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
                articles.append(
                    {
                        "title": content.get("title"),
                        "summary": content.get("summary"),
                        "publisher": provider.get("displayName"),
                        "url": url_obj.get("url"),
                        "published_at": content.get("pubDate"),
                    }
                )
            else:
                articles.append(
                    {
                        "title": item.get("title"),
                        "summary": item.get("summary"),
                        "publisher": item.get("publisher"),
                        "url": item.get("link"),
                        "published_at": item.get("providerPublishTime"),
                    }
                )
        self.cache.set("news", cache_key, articles, ttl_seconds=DEFAULT_TTLS["news"])
        return articles

    def get_chart(self, ticker: str, period: str = "1mo", interval: str = "1d") -> dict[str, Any]:
        symbol = ticker.upper().strip()
        cache_key = f"{symbol}:{period}:{interval}"
        cached = self.cache.get("quotes", f"chart:{cache_key}")
        if cached is not None:
            return cached
        import yfinance as yf

        history = yf.Ticker(symbol).history(period=period, interval=interval)
        if history is None or history.empty:
            payload = {"ticker": symbol, "period": period, "interval": interval, "points": []}
        else:
            frame = history.reset_index()
            points = []
            for _, row in frame.iterrows():
                points.append(
                    {
                        "date": str(row.iloc[0]),
                        "open": _to_float(row.get("Open")),
                        "high": _to_float(row.get("High")),
                        "low": _to_float(row.get("Low")),
                        "close": _to_float(row.get("Close")),
                        "volume": _to_float(row.get("Volume")),
                    }
                )
            payload = {"ticker": symbol, "period": period, "interval": interval, "points": points}
        self.cache.set("quotes", f"chart:{cache_key}", payload, ttl_seconds=DEFAULT_TTLS["quotes"])
        return payload

    def get_earnings(self, ticker: str) -> dict[str, Any]:
        symbol = ticker.upper().strip()
        import yfinance as yf

        stock = yf.Ticker(symbol)
        dates = getattr(stock, "earnings_dates", None)
        rows = _jsonable(dates) if dates is not None else []
        return {"ticker": symbol, "earnings_dates": rows, "source": "yfinance"}

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
        cached = self.cache.get("indices", "major_us_indices")
        if cached is not None:
            return cached
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ Composite": "^IXIC",
            "Dow Jones Industrial Average": "^DJI",
            "Russell 2000": "^RUT",
        }
        data = []
        for name, symbol in indices.items():
            try:
                quote = self.get_quote(symbol)
                data.append({"name": name, "symbol": symbol, **quote})
            except Exception as exc:
                data.append({"name": name, "symbol": symbol, "error": str(exc)})
        self.cache.set("indices", "major_us_indices", data, ttl_seconds=DEFAULT_TTLS["indices"])
        return data

    def get_market_movers(self, limit: int = 10) -> dict[str, Any]:
        universe = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD", "NFLX", "JPM", "UNH", "XOM", "LLY"]
        movers = []
        for symbol in universe:
            try:
                quote = self.get_quote(symbol)
                if quote.get("change_pct") is not None:
                    movers.append(quote)
            except Exception:
                continue
        gainers = sorted(movers, key=lambda row: row.get("change_pct") or 0, reverse=True)[:limit]
        losers = sorted(movers, key=lambda row: row.get("change_pct") or 0)[:limit]
        return {"gainers": gainers, "losers": losers, "source": "curated US large-cap universe via yfinance"}

    def get_market_summary(self) -> dict[str, Any]:
        indices = self.get_market_indices()
        movers = self.get_market_movers(limit=5)
        return {"indices": indices, "movers": movers, "generated_at": _now_iso()}

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

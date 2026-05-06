"""Deterministic local demo data for IMPERIA presentation mode.

Demo mode keeps the capstone project reliable during presentations and grading
when free external providers are down, rate-limited, or missing API keys. The
fixtures are educational samples, not live market data.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

DEMO_SOURCE = "IMPERIA demo fixture"
DEMO_WARNING = "Demo mode enabled: sample educational data, not live market data."


def is_demo_mode() -> bool:
    """Return true when deterministic demo data should replace live providers."""

    return os.getenv("IMPERIA_DEMO_MODE", "false").lower() in {"1", "true", "yes", "on"}


def _demo_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "demo"


@lru_cache(maxsize=None)
def _load_json(name: str) -> Any:
    path = _demo_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


def demo_universe() -> list[str]:
    """Return the educational demo universe of popular US stocks and ETFs."""

    return [str(item).upper().replace(".", "-") for item in _load_json("demo_universe.json")]


def _idx(symbol: str) -> int:
    universe = demo_universe()
    try:
        return universe.index(symbol.upper().replace(".", "-"))
    except ValueError:
        return abs(sum(ord(char) for char in symbol.upper())) % 100


def _profile(symbol: str) -> dict[str, Any]:
    profiles = _load_json("profiles.json")
    normalized = symbol.upper().replace(".", "-")
    fixture = profiles.get(normalized, {})
    sector = fixture.get("sector")
    if not sector:
        sectors = ["Technology", "Financial Services", "Healthcare", "Consumer Cyclical", "Industrials", "Communication Services"]
        sector = sectors[_idx(normalized) % len(sectors)]
    return {
        "ticker": normalized,
        "name": fixture.get("name") or f"{normalized} Demo Company",
        "exchange": "NASDAQ" if _idx(normalized) % 2 else "NYSE",
        "sector": sector,
        "industry": fixture.get("industry") or f"{sector} Demo Industry",
        "website": f"https://example.com/demo/{normalized.lower()}",
        "summary": f"Sample IMPERIA demo profile for {normalized}. This is deterministic educational data.",
        "source": DEMO_SOURCE,
        "warnings": [DEMO_WARNING],
    }


def get_demo_profile(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    return _profile(symbol)


def get_demo_quote(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    fixture = _load_json("quotes.json").get(symbol, {})
    index = _idx(symbol)
    price = float(fixture.get("price") or (38 + index * 4.75))
    change_pct = float(fixture.get("change_pct") if fixture.get("change_pct") is not None else ((index % 9) - 4) * 0.42)
    previous_close = price / (1 + change_pct / 100) if change_pct != -100 else price
    return {
        "ticker": symbol,
        "price": round(price, 2),
        "change": round(price - previous_close, 2),
        "change_pct": round(change_pct, 2),
        "volume": fixture.get("volume") or int(5_000_000 + index * 350_000),
        "market_cap": fixture.get("market_cap") if fixture.get("market_cap") is not None else float(25_000_000_000 + index * 7_500_000_000),
        "day_high": round(price * 1.018, 2),
        "day_low": round(price * 0.982, 2),
        "fifty_two_week_high": round(price * 1.24, 2),
        "fifty_two_week_low": round(price * 0.72, 2),
        "avg_volume": int(4_500_000 + index * 320_000),
        "previous_close": round(previous_close, 2),
        "source": DEMO_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "warnings": [DEMO_WARNING],
    }


def get_demo_metrics(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    fixture = _load_json("metrics.json").get(symbol, {})
    index = _idx(symbol)
    metrics = {
        "pe": round(fixture.get("pe", 14 + (index % 34) * 1.1), 2),
        "forward_pe": round(fixture.get("forward_pe", 12 + (index % 30) * 0.95), 2),
        "eps": round(fixture.get("eps", 2.1 + (index % 15) * 0.38), 2),
        "revenue_growth": round(fixture.get("revenue_growth", 0.02 + (index % 12) * 0.012), 4),
        "gross_margin": round(fixture.get("gross_margin", 0.28 + (index % 20) * 0.012), 4),
        "operating_margin": round(fixture.get("operating_margin", 0.10 + (index % 18) * 0.009), 4),
        "net_margin": round(fixture.get("net_margin", 0.06 + (index % 16) * 0.008), 4),
        "roe": round(fixture.get("roe", 0.08 + (index % 15) * 0.015), 4),
        "roa": round(fixture.get("roa", 0.04 + (index % 12) * 0.007), 4),
        "debt_to_equity": round(fixture.get("debt_to_equity", 15 + (index % 45) * 1.7), 2),
        "current_ratio": round(fixture.get("current_ratio", 0.9 + (index % 20) * 0.08), 2),
        "quick_ratio": round(fixture.get("quick_ratio", 0.7 + (index % 18) * 0.07), 2),
        "free_cash_flow_margin": round(fixture.get("free_cash_flow_margin", 0.04 + (index % 18) * 0.009), 4),
        "ev_to_ebitda": round(fixture.get("ev_to_ebitda", 10 + (index % 28) * 0.8), 2),
    }
    quote = get_demo_quote(symbol) or {}
    revenue = float(12_000_000_000 + index * 1_200_000_000)
    net_income = revenue * metrics["net_margin"]
    fcf = revenue * metrics["free_cash_flow_margin"]
    return {
        "ticker": symbol,
        "profile": _profile(symbol),
        "metrics": metrics,
        "ttm": {
            "revenue": revenue,
            "net_income": net_income,
            "free_cash_flow": fcf,
        },
        "balance_sheet_snapshot": {
            "assets": revenue * 1.8,
            "equity": revenue * 0.75,
            "total_debt": revenue * metrics["debt_to_equity"] / 100,
            "cash": revenue * 0.16,
        },
        "formula_metadata": {
            "pe": "market_cap / trailing_twelve_month_net_income",
            "net_margin": "ttm_net_income / ttm_revenue",
            "free_cash_flow_margin": "ttm_free_cash_flow / ttm_revenue",
        },
        "citations": [demo_citation("financial_metrics", f"{symbol} demo financial metrics", ticker=symbol)],
        "warnings": [DEMO_WARNING],
        "sources": [DEMO_SOURCE],
        "market_cap": quote.get("market_cap"),
    }


def get_demo_news(ticker: str, *, limit: int = 20, window: str = "today") -> list[dict[str, Any]]:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return []
    fixture = _load_json("news.json").get(symbol) or []
    if not fixture:
        fixture = [
            {
                "title": f"{symbol} demo brief: market watches earnings, filings, and sector context",
                "summary": f"Sample IMPERIA demo story for {symbol}.",
                "sentiment_label": "neutral",
            }
        ]
    now = datetime.now(timezone.utc)
    rows = []
    for offset, item in enumerate(fixture[:limit]):
        published = now - timedelta(hours=offset + 1)
        rows.append(
            {
                "title": item["title"],
                "url": f"https://example.com/imperia-demo/{symbol.lower()}/{offset + 1}",
                "source": "IMPERIA Demo News",
                "provider": DEMO_SOURCE,
                "published_at": published.isoformat(),
                "summary": item.get("summary"),
                "snippet": item.get("summary"),
                "sentiment": item.get("sentiment_label"),
                "sentiment_label": item.get("sentiment_label"),
                "tickers_mentioned": [symbol],
                "tickers": [symbol],
                "citation_id": f"demo-news-{symbol.lower()}-{offset + 1}",
                "warnings": [DEMO_WARNING],
            }
        )
    return rows


def get_demo_earnings(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    fixture = _load_json("earnings.json").get(symbol, {})
    next_event = fixture.get("next") or {"report_date": (date.today() + timedelta(days=45)).isoformat(), "estimated_eps": 1.0 + _idx(symbol) * 0.03}
    history = fixture.get("history") or [
        {"period": "2026Q1", "actual_eps": 1.12, "estimated_eps": 1.05, "surprise_pct": 6.7, "beat_miss": "beat"}
    ]
    return {
        "next": {
            "ticker": symbol,
            "company_name": _profile(symbol)["name"],
            "report_date": next_event.get("report_date"),
            "time_of_day": "unknown",
            "estimated_eps": next_event.get("estimated_eps"),
            "consensus_revenue_estimate": None,
            "source": DEMO_SOURCE,
            "warnings": [DEMO_WARNING],
        },
        "history": [
            {
                "ticker": symbol,
                "fiscal_period": item.get("period"),
                "report_date": item.get("period"),
                "actual_eps": item.get("actual_eps"),
                "estimated_eps": item.get("estimated_eps"),
                "surprise_pct": item.get("surprise_pct"),
                "beat_miss": item.get("beat_miss", "unknown"),
                "source": DEMO_SOURCE,
            }
            for item in history
        ],
    }


def get_demo_filings(ticker: str, *, filing_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return []
    fixture = _load_json("filings.json").get(symbol) or [
        {"filing_type": "10-Q", "filing_date": date.today().isoformat(), "summary": f"Sample filing summary for {symbol}."}
    ]
    rows = []
    for index, item in enumerate(fixture):
        if filing_type and item.get("filing_type", "").upper() != filing_type.upper():
            continue
        rows.append(
            {
                "ticker": symbol,
                "cik": f"{1_000_000 + _idx(symbol):010d}",
                "accession_number": f"demo-{symbol.lower()}-{index + 1}",
                "filing_type": item.get("filing_type"),
                "filing_date": item.get("filing_date"),
                "report_date": item.get("filing_date"),
                "primary_document": "demo-filing.htm",
                "url": f"https://example.com/imperia-demo/sec/{symbol.lower()}/{index + 1}",
                "summary": item.get("summary"),
                "source": DEMO_SOURCE,
                "warnings": [DEMO_WARNING],
            }
        )
    return rows[:limit]


def get_demo_sentiment(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    fixture = _load_json("sentiment.json").get(symbol)
    if fixture:
        payload = dict(fixture)
    else:
        labels = ["bullish", "neutral", "bearish", "mixed"]
        label = labels[_idx(symbol) % len(labels)]
        payload = {
            "sentiment_label": label,
            "confidence_score": 55 + (_idx(symbol) % 25),
            "summary": f"Demo sentiment for {symbol} is {label}; review price action, filings, earnings, and news before drawing conclusions.",
        }
    payload.update({"provider": DEMO_SOURCE, "ticker": symbol, "warnings": [DEMO_WARNING]})
    return payload


def get_demo_research_report(ticker: str) -> dict[str, Any] | None:
    symbol = ticker.upper().replace(".", "-")
    if symbol not in demo_universe():
        return None
    fixture = _load_json("research_reports.json").get(symbol, {})
    summary = fixture.get("executive_summary") or f"Demo research report for {symbol}."
    citations = [
        demo_citation("market_data", f"{symbol} demo quote", ticker=symbol),
        demo_citation("sec", f"{symbol} demo SEC filing", ticker=symbol),
        demo_citation("news", f"{symbol} demo news", ticker=symbol),
    ]
    return {
        "ticker": symbol,
        "status": "completed",
        "executive_summary": summary,
        "what_happened_recently": f"{symbol} demo data shows a recent move explained by sample news, earnings, and sector context.",
        "company_overview": _profile(symbol),
        "financial_analysis": get_demo_metrics(symbol),
        "sec_filing_insights": {"filings": get_demo_filings(symbol, limit=3), "warnings": [DEMO_WARNING]},
        "earnings_analysis": get_demo_earnings(symbol),
        "news_context": get_demo_news(symbol, limit=5),
        "prediction_market_sentiment": get_demo_sentiment(symbol),
        "bull_thesis": f"The demo bull case for {symbol} depends on durable growth, margin discipline, and execution.",
        "bear_thesis": f"The demo bear case for {symbol} centers on valuation, execution risk, and macro sensitivity.",
        "key_risks": ["Valuation risk", "Execution risk", "Macro/sector risk"],
        "what_to_watch_next": ["Next earnings report", "Recent SEC filings", "Sector performance", "News flow"],
        "data_quality_warnings": [DEMO_WARNING],
        "citations": citations,
        "agent_outputs": {},
    }


def get_demo_ohlcv(ticker: str, *, periods: int = 30) -> pd.DataFrame | None:
    symbol = ticker.upper().replace(".", "-")
    quote = get_demo_quote(symbol)
    if quote is None:
        return None
    end = pd.Timestamp.utcnow().normalize()
    dates = pd.date_range(end=end, periods=periods, freq="D")
    base = float(quote["price"])
    rows = []
    for index, dt in enumerate(dates):
        drift = (index - periods + 1) * 0.004
        close = base * (1 + drift)
        rows.append(
            {
                "Open": close * 0.995,
                "High": close * 1.01,
                "Low": close * 0.99,
                "Close": close,
                "Volume": quote["avg_volume"],
            }
        )
    return pd.DataFrame(rows, index=dates)


def demo_citation(source_type: str, title: str, *, ticker: str | None = None) -> dict[str, Any]:
    """Return a structured citation for sample demo data."""

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": f"demo-{source_type}-{(ticker or 'market').lower()}",
        "source_type": source_type,
        "provider": DEMO_SOURCE,
        "title": title,
        "url": f"https://example.com/imperia-demo/{(ticker or 'market').lower()}",
        "snippet": DEMO_WARNING,
        "timestamp": now,
        "accessed_at": now,
        "ticker": ticker,
        "confidence": 0.7,
        "metadata": {"demo": True},
    }


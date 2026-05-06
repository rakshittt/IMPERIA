"""Stock-first research assembly helpers for IMPERIA API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tradingagents.dataflows import earnings_data, market_data, news_aggregator
from tradingagents.dataflows.computed_metrics import compute_financial_metrics
from tradingagents.dataflows.sec_edgar import get_sec_filings
from tradingagents.engine.safety import DISCLAIMER, sanitize_answer
from tradingagents.engine.stock_sentiment import get_stock_sentiment
from tradingagents.utils.validation import normalize_ticker


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _citation(source_type: str, provider: str, title: str, url: str | None, ticker: str) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "provider": provider,
        "title": title,
        "url": url,
        "ticker": ticker,
        "accessed_at": _now(),
    }


def _profile_from_metrics(metrics: dict[str, Any], ticker: str) -> dict[str, Any]:
    return metrics.get("profile") or {"ticker": ticker, "name": ticker}


def _get_news(ticker: str, window: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        return [item.model_dump() for item in news_aggregator.get_stock_news(ticker, limit=limit, window=window)]
    except TypeError:
        return [item.model_dump() for item in news_aggregator.get_stock_news(ticker, limit=limit)]


def build_what_happened(ticker: str, *, window: str = "today") -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    window = news_aggregator.normalize_news_window(window)
    quote = market_data.get_quote(symbol).model_dump()
    news = _get_news(symbol, window, limit=8)
    sentiment = get_stock_sentiment(symbol, window=window).model_dump()
    citations = [
        _citation("market_data", quote.get("source", "market_data"), f"{symbol} quote", f"https://finance.yahoo.com/quote/{symbol}", symbol)
    ]
    citations.extend(
        _citation("news", item.get("provider") or item.get("source") or "news", item.get("title") or "News article", item.get("url"), symbol)
        for item in news[:5]
    )
    move = quote.get("change_pct")
    move_text = f"moved {move:+.2f}%" if move is not None else "has limited live price-move data available"
    headline_text = "; ".join(item.get("title", "") for item in news[:3] if item.get("title")) or "No recent articles were found in this window."
    answer = sanitize_answer(
        f"{symbol} {move_text} in the selected window. Key items to review: {headline_text} "
        f"The combined research sentiment is {sentiment.get('sentiment_label', 'uncertain')}. {DISCLAIMER}"
    )
    warnings = quote.get("warnings", []) + sentiment.get("warnings", [])
    if not news:
        warnings.append(f"No news found for {symbol} in window {window}.")
    return {
        "answer": answer,
        "ticker": symbol,
        "time_window": window,
        "price_action": quote,
        "key_news": news,
        "sentiment": sentiment,
        "citations": citations + sentiment.get("citations", []),
        "warnings": warnings,
        "providers_used": sorted({quote.get("source", "market_data")} | {item.get("provider") or item.get("source") for item in news if item.get("provider") or item.get("source")}),
    }


def build_research_snapshot(ticker: str, *, window: str = "today") -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    window = news_aggregator.normalize_news_window(window)
    quote = market_data.get_quote(symbol).model_dump()
    metrics = compute_financial_metrics(symbol)
    earnings = build_earnings_brief(symbol)
    filing = build_filing_brief(symbol)
    news = _get_news(symbol, window, limit=5)
    sentiment = get_stock_sentiment(symbol, window=window).model_dump()
    citations = [
        _citation("market_data", quote.get("source", "market_data"), f"{symbol} quote", f"https://finance.yahoo.com/quote/{symbol}", symbol),
        *metrics.get("citations", []),
        *filing.get("citations", []),
        *earnings.get("citations", []),
        *sentiment.get("citations", []),
    ]
    return {
        "ticker": symbol,
        "company_name": _profile_from_metrics(metrics, symbol).get("name"),
        "what_happened_today": build_what_happened(symbol, window=window)["answer"],
        "price_action": quote,
        "key_news": news,
        "fundamental_snapshot": metrics,
        "latest_earnings_context": earnings,
        "latest_sec_filing_context": filing,
        "sentiment_label": sentiment.get("sentiment_label"),
        "risks_to_watch": build_risks(symbol)["risks"],
        "citations": citations,
        "warnings": quote.get("warnings", []) + metrics.get("warnings", []) + sentiment.get("warnings", []),
        "providers_used": sorted({quote.get("source", "market_data"), "SEC EDGAR", "free_earnings_data"}),
    }


def build_risks(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    metrics = compute_financial_metrics(symbol)
    filings = get_sec_filings(symbol, limit=5)
    risk_items = [
        "Valuation risk: compare P/E and EV/EBITDA against growth and margins.",
        "Earnings risk: watch estimate revisions, surprise history, and guidance commentary.",
        "Filing risk: review recent 10-K/10-Q/8-K disclosures for material changes.",
        "Market risk: sector and broad-index moves can dominate company-specific signals.",
    ]
    metric_values = metrics.get("metrics", {})
    if metric_values.get("debt_to_equity") and metric_values["debt_to_equity"] > 100:
        risk_items.append("Balance-sheet risk: debt/equity is elevated in available data.")
    citations = [
        _citation("sec", "SEC EDGAR", filing.get("filing_type") or "SEC filing", filing.get("url"), symbol)
        for filing in filings[:5]
    ]
    citations.extend(metrics.get("citations", []))
    return {
        "ticker": symbol,
        "risks": risk_items,
        "sec_risk_highlights": [filing.get("summary") or f"{filing.get('filing_type')} filed {filing.get('filing_date')}" for filing in filings[:3]],
        "financial_risks": {"debt_to_equity": metric_values.get("debt_to_equity"), "current_ratio": metric_values.get("current_ratio")},
        "citations": citations,
        "warnings": metrics.get("warnings", []),
    }


def build_bull_bear(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    metrics = compute_financial_metrics(symbol)
    sentiment = get_stock_sentiment(symbol).model_dump()
    metric_values = metrics.get("metrics", {})
    bull = [
        "Bull thesis: stronger revenue growth, margins, earnings execution, and positive news flow could support the research case.",
        f"Available revenue growth input: {metric_values.get('revenue_growth')}.",
        f"Research sentiment: {sentiment.get('sentiment_label', 'uncertain')}.",
    ]
    bear = [
        "Bear thesis: valuation, execution risk, weaker earnings quality, or adverse filings/news could pressure the research case.",
        f"Available P/E input: {metric_values.get('pe')}.",
        "Free-provider gaps may reduce confidence if key metrics are unavailable.",
    ]
    return {
        "ticker": symbol,
        "bull_thesis": bull,
        "bear_thesis": bear,
        "assumptions": ["Educational research framing only; no buy/sell/hold recommendation is provided."],
        "risks": build_risks(symbol)["risks"],
        "citations": metrics.get("citations", []) + sentiment.get("citations", []),
        "warnings": metrics.get("warnings", []) + sentiment.get("warnings", []),
    }


def build_earnings_brief(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    next_event = earnings_data.get_next_earnings(symbol)
    history = [item.model_dump() for item in earnings_data.get_earnings_history(symbol, limit=8)]
    stats = earnings_data.get_earnings_surprise_stats(symbol).model_dump()
    return {
        "ticker": symbol,
        "next_earnings": next_event.model_dump() if next_event else None,
        "history": history,
        "surprise_stats": stats,
        "things_to_watch": ["EPS versus estimate", "Revenue growth", "Margin commentary", "Forward guidance", "Management tone"],
        "citations": [_citation("earnings", stats.get("source", "free_earnings_data"), f"{symbol} earnings data", f"https://finance.yahoo.com/quote/{symbol}/analysis", symbol)],
        "warnings": stats.get("warnings", []),
    }


def build_filing_brief(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    filings = get_sec_filings(symbol, limit=10)
    latest = filings[:3]
    return {
        "ticker": symbol,
        "latest_filings": latest,
        "summary": "Recent SEC filings are listed for review. IMPERIA highlights metadata and available filing summaries without fabricating unavailable sections.",
        "important_risks": [item.get("summary") for item in latest if item.get("summary")] or ["Review latest 10-K/10-Q risk factors and MD&A for material changes."],
        "citations": [_citation("sec", "SEC EDGAR", item.get("filing_type") or "SEC filing", item.get("url"), symbol) for item in latest],
        "warnings": [] if latest else [f"No recent SEC filings available for {symbol} from configured free sources."],
    }


def build_investor_checklist(ticker: str) -> dict[str, Any]:
    symbol = normalize_ticker(ticker)
    metrics = compute_financial_metrics(symbol)
    filing = build_filing_brief(symbol)
    earnings = build_earnings_brief(symbol)
    return {
        "ticker": symbol,
        "title": f"{symbol} research checklist",
        "not_investment_advice": True,
        "valuation_checklist": ["Compare P/E, forward P/E, PEG, and EV/EBITDA with growth and margins."],
        "growth_checklist": ["Review revenue growth, segment trends, and market share evidence."],
        "profitability_checklist": ["Review gross margin, operating margin, net margin, ROE, and ROA."],
        "balance_sheet_checklist": ["Review debt/equity, current ratio, quick ratio, cash, and refinancing risk."],
        "earnings_checklist": earnings.get("things_to_watch", []),
        "risk_checklist": build_risks(symbol)["risks"],
        "news_checklist": ["Check whether news is confirmed by filings, earnings, or official company disclosures."],
        "source_links": [citation.get("url") for citation in filing.get("citations", []) if citation.get("url")],
        "citations": metrics.get("citations", []) + filing.get("citations", []) + earnings.get("citations", []),
        "warnings": metrics.get("warnings", []) + filing.get("warnings", []) + earnings.get("warnings", []),
    }


def compare_stocks(ticker_a: str, ticker_b: str) -> dict[str, Any]:
    left = normalize_ticker(ticker_a)
    right = normalize_ticker(ticker_b)
    left_metrics = compute_financial_metrics(left)
    right_metrics = compute_financial_metrics(right)
    left_sentiment = get_stock_sentiment(left).model_dump()
    right_sentiment = get_stock_sentiment(right).model_dump()
    keys = ["pe", "forward_pe", "revenue_growth", "gross_margin", "net_margin", "roe", "debt_to_equity"]
    comparison = {
        key: {
            left: left_metrics.get("metrics", {}).get(key),
            right: right_metrics.get("metrics", {}).get(key),
        }
        for key in keys
    }
    return {
        "ticker_a": left,
        "ticker_b": right,
        "valuation_comparison": {key: comparison[key] for key in ["pe", "forward_pe"]},
        "growth_comparison": {"revenue_growth": comparison["revenue_growth"]},
        "profitability_comparison": {key: comparison[key] for key in ["gross_margin", "net_margin", "roe"]},
        "balance_sheet_comparison": {"debt_to_equity": comparison["debt_to_equity"]},
        "sentiment_comparison": {left: left_sentiment.get("sentiment_label"), right: right_sentiment.get("sentiment_label")},
        "risks": {left: build_risks(left)["risks"], right: build_risks(right)["risks"]},
        "citations": left_metrics.get("citations", []) + right_metrics.get("citations", []) + left_sentiment.get("citations", []) + right_sentiment.get("citations", []),
        "warnings": left_metrics.get("warnings", []) + right_metrics.get("warnings", []) + left_sentiment.get("warnings", []) + right_sentiment.get("warnings", []),
    }


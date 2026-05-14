import pytest

from tradingagents.engine.citation_tracker import CitationTracker, attach_citations
from tradingagents.core.query.router import route_query
from tradingagents.engine.search import ticker_resolver


@pytest.mark.unit
def test_citation_tracker_deduplicates_and_attaches():
    tracker = CitationTracker()
    tracker.add("sec", title="AAPL 10-K", url="https://sec.gov/aapl")
    tracker.add("sec", title="AAPL 10-K", url="https://sec.gov/aapl")
    response = attach_citations({"answer": "ok"}, tracker)
    assert len(response["citations"]) == 1
    assert response["citations"][0]["source_type"] == "sec"


@pytest.mark.unit
def test_query_router_fast_and_deep_examples():
    assert route_query("What is Apple's P/E ratio?").mode == "fast"
    assert route_query("Top US market movers today").mode == "fast"
    assert route_query("Should I buy AMD over NVDA?").mode == "deep"
    assert route_query("Give me a bull vs bear thesis on MSFT").mode == "deep"


@pytest.mark.unit
def test_ticker_resolver_exact_alias_fuzzy_and_unsupported(monkeypatch):
    monkeypatch.setattr(
        ticker_resolver,
        "_symbol_universe",
        lambda: list(ticker_resolver.POPULAR_US_SYMBOLS.values()) + list(ticker_resolver.MAJOR_US_ETFS.values()),
    )
    assert ticker_resolver.resolve_ticker("Apple")["ticker"] == "AAPL"
    assert ticker_resolver.resolve_ticker("SPY")["security_type"] == "ETF"
    assert ticker_resolver.search_symbols("Micro", limit=1)[0]["ticker"] == "MSFT"
    assert ticker_resolver.resolve_ticker("BTC")["supported"] is False

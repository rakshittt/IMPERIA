import pytest

from tradingagents.cache.sqlite_cache import SQLiteCache
from tradingagents.dataflows import screener
from tradingagents.dataflows.market_data import QuoteData


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    monkeypatch.setattr(screener, "get_default_cache", lambda: cache)
    return cache


@pytest.mark.unit
def test_parse_nl_screener_query_deterministic(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    criteria = screener.parse_nl_screener_query("profitable tech stocks with P/E under 20 and revenue growth > 10%")
    assert criteria.max_pe == 20
    assert criteria.min_revenue_growth == 0.10
    assert criteria.min_net_margin == 0
    assert criteria.sectors == ["Technology"]


@pytest.mark.unit
def test_parse_nl_screener_query_deepseek_merge(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")

    monkeypatch.setattr(screener, "deepseek_text", lambda *args, **kwargs: "{\"max_pe\": 15, \"limit\": 5}")
    assert screener.parse_nl_screener_query("cheap stocks").max_pe == 15


@pytest.mark.unit
def test_screen_stocks_filters_and_ranks(cache, monkeypatch):
    monkeypatch.setattr(screener, "load_universe", lambda: ["AAA", "BBB"])
    monkeypatch.setattr(screener, "get_quote", lambda ticker: QuoteData(ticker=ticker, market_cap=200 if ticker == "AAA" else 100))
    monkeypatch.setattr(
        screener,
        "compute_financial_metrics",
        lambda ticker: {
            "profile": {"sector": "Technology" if ticker == "AAA" else "Energy"},
            "metrics": {"pe": 10 if ticker == "AAA" else 30, "gross_margin": 0.5},
            "warnings": [],
        },
    )
    result = screener.screen_stocks(screener.ScreenerCriteria(sectors=["Technology"], max_pe=20))
    assert [item.ticker for item in result] == ["AAA"]


@pytest.mark.unit
def test_screen_stocks_respects_uncached_cap(cache, monkeypatch):
    monkeypatch.setattr(screener, "load_universe", lambda: [f"T{i}" for i in range(60)])
    calls = []
    monkeypatch.setattr(screener, "get_quote", lambda ticker: calls.append(ticker) or QuoteData(ticker=ticker, market_cap=1))
    monkeypatch.setattr(screener, "compute_financial_metrics", lambda ticker: {"metrics": {}, "warnings": []})
    screener.screen_stocks(screener.ScreenerCriteria())
    assert len(calls) == screener.MAX_UNCACHED_FETCHES


@pytest.mark.unit
def test_screen_stocks_partial_results_warning(cache, monkeypatch):
    monkeypatch.setattr(screener, "load_universe", lambda: [f"T{i}" for i in range(55)])
    monkeypatch.setattr(screener, "get_quote", lambda ticker: QuoteData(ticker=ticker, market_cap=1))
    monkeypatch.setattr(screener, "compute_financial_metrics", lambda ticker: {"metrics": {}, "warnings": []})
    result = screener.screen_stocks(screener.ScreenerCriteria(limit=5))
    assert "Partial results" in result[0].warnings[-1]


@pytest.mark.unit
def test_screener_criteria_rejects_invalid_bounds():
    with pytest.raises(ValueError):
        screener.ScreenerCriteria(min_market_cap=10, max_market_cap=1)


@pytest.mark.unit
def test_screen_stocks_uses_cached_metrics(cache, monkeypatch):
    cache.set("screener_metrics", "metrics:AAPL", {"ticker": "AAPL", "market_cap": 10, "metrics": {"pe": 5}}, ttl_seconds=100)
    monkeypatch.setattr(screener, "load_universe", lambda: ["AAPL"])
    result = screener.screen_stocks(screener.ScreenerCriteria(max_pe=10))
    assert result[0].ticker == "AAPL"

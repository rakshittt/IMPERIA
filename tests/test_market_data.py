import pandas as pd
import pytest

from tradingagents.cache.sqlite_cache import SQLiteCache
from tradingagents.dataflows import market_data


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    monkeypatch.setattr(market_data, "get_default_cache", lambda: cache)
    return cache


@pytest.mark.unit
def test_get_quote_uses_cache(cache):
    cache.set("quotes", "AAPL", {"ticker": "AAPL", "price": 10, "source": "cache"}, ttl_seconds=60)
    assert market_data.get_quote("AAPL").price == 10


@pytest.mark.unit
def test_get_quote_falls_back_to_finnhub(cache, monkeypatch):
    monkeypatch.setattr(market_data, "_quote_from_yfinance", lambda ticker: (_ for _ in ()).throw(RuntimeError("yf")))
    monkeypatch.setattr(market_data, "get_finnhub_quote", lambda ticker: {"price": 11, "source": "finnhub_free_tier"})
    monkeypatch.setattr(market_data, "get_alpha_vantage_quote", lambda ticker: {"price": 12, "source": "alpha"})
    quote = market_data.get_quote("AAPL")
    assert quote.price == 11
    assert quote.source == "finnhub_free_tier"


@pytest.mark.unit
def test_get_batch_quotes_splits_over_50(cache, monkeypatch):
    seen = []
    monkeypatch.setattr(market_data, "_retry", lambda func: (_ for _ in ()).throw(RuntimeError("batch")))

    def fake_quote(ticker):
        seen.append(ticker)
        return market_data.QuoteData(ticker=ticker, price=1)

    monkeypatch.setattr(market_data, "get_quote", fake_quote)
    result = market_data.get_batch_quotes([f"T{i}" for i in range(60)])
    assert len(result) == 60
    assert len(seen) == 60


@pytest.mark.unit
def test_movers_and_breadth_from_batch_quotes(cache, monkeypatch):
    monkeypatch.setattr(market_data, "load_universe", lambda limit=None: ["AAA", "BBB", "CCC"])
    monkeypatch.setattr(
        market_data,
        "get_batch_quotes",
        lambda tickers: {
            "AAA": market_data.QuoteData(ticker="AAA", change_pct=2),
            "BBB": market_data.QuoteData(ticker="BBB", change_pct=-1),
            "CCC": market_data.QuoteData(ticker="CCC", change_pct=0),
        },
    )
    movers = market_data.get_market_movers(1)
    breadth = market_data.get_market_breadth()
    assert movers.gainers[0].ticker == "AAA"
    assert movers.losers[0].ticker == "BBB"
    assert breadth.advancing == 1 and breadth.declining == 1 and breadth.unchanged == 1


@pytest.mark.unit
def test_market_breadth_chunks_full_universe(cache, monkeypatch):
    monkeypatch.setattr(market_data, "load_universe", lambda limit=None: [f"T{i}" for i in range(75)])
    seen = []

    def fake_batch(tickers):
        seen.append(list(tickers))
        return {ticker: market_data.QuoteData(ticker=ticker, change_pct=1) for ticker in tickers}

    monkeypatch.setattr(market_data, "get_batch_quotes", fake_batch)
    breadth = market_data.get_market_breadth()
    assert len(seen) == 2
    assert breadth.advancing == 75


@pytest.mark.unit
def test_market_indices_include_vix(cache, monkeypatch):
    monkeypatch.setattr(
        market_data,
        "get_batch_quotes",
        lambda tickers: {ticker: market_data.QuoteData(ticker=ticker, price=20, change_pct=1) for ticker in tickers},
    )
    indices = market_data.get_market_indices()
    assert any(item.symbol == "^VIX" for item in indices)


@pytest.mark.unit
def test_market_movers_tolerates_partial_batch_failure(cache, monkeypatch):
    monkeypatch.setattr(market_data, "load_universe", lambda limit=None: ["AAA", "BBB", "CCC"])

    def fake_batch(tickers):
        if "BBB" in tickers:
            raise RuntimeError("partial")
        return {ticker: market_data.QuoteData(ticker=ticker, change_pct=1) for ticker in tickers}

    monkeypatch.setattr(market_data, "get_batch_quotes", fake_batch)
    movers = market_data.get_market_movers(2)
    assert movers.gainers == []
    assert "Batch 1 failed" in movers.warnings[0]


@pytest.mark.unit
def test_sector_performance_and_ohlcv_records(cache, monkeypatch):
    monkeypatch.setattr(
        market_data,
        "get_batch_quotes",
        lambda tickers: {ticker: market_data.QuoteData(ticker=ticker, price=10, change_pct=1) for ticker in tickers},
    )
    assert len(market_data.get_sector_performance()) == len(market_data.SECTOR_ETFS)
    frame = pd.DataFrame({"Open": [1], "High": [2], "Low": [0.5], "Close": [1.5], "Volume": [100]}, index=pd.to_datetime(["2026-01-01"]))
    assert market_data.ohlcv_to_records(frame)[0]["close"] == 1.5

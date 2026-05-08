import pandas as pd
import pytest

from tradingagents.cache.sqlite_cache import SQLiteCache
from tradingagents.dataflows import earnings_data


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    monkeypatch.setattr(earnings_data, "get_default_cache", lambda: cache)
    return cache


@pytest.mark.unit
def test_finnhub_calendar(cache, monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "key")
    monkeypatch.setattr(earnings_data, "_get_json", lambda url, params: {"earningsCalendar": [{"symbol": "AAPL", "date": "2026-01-01", "epsEstimate": 1.2, "hour": "amc"}]})
    events = earnings_data.get_earnings_calendar(start_date="2026-01-01", end_date="2026-01-02", tickers=["AAPL"])
    assert events[0].time_of_day == "AMC"


@pytest.mark.unit
def test_finnhub_history(cache, monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "key")
    monkeypatch.setattr(earnings_data, "_get_json", lambda url, params: [{"period": "2025-Q4", "actual": 2, "estimate": 1, "surprisePercent": 100}])
    assert earnings_data.get_earnings_history("AAPL")[0].beat_miss == "beat"


@pytest.mark.unit
def test_yfinance_history_fallback(cache, monkeypatch):
    monkeypatch.setattr(earnings_data, "_finnhub_history", lambda ticker: [])

    class FakeTicker:
        earnings_dates = pd.DataFrame({"Reported EPS": [1], "EPS Estimate": [2], "Surprise(%)": [-50]}, index=pd.to_datetime(["2026-01-01"]))

    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda ticker: FakeTicker())
    assert earnings_data.get_earnings_history("AAPL")[0].beat_miss == "miss"


@pytest.mark.unit
def test_next_earnings_uses_calendar(cache, monkeypatch):
    monkeypatch.setattr(earnings_data, "_finnhub_calendar", lambda start, end, tickers: [earnings_data.EarningsEvent(ticker="AAPL", report_date="2026-01-01")])
    assert earnings_data.get_next_earnings("AAPL").report_date == "2026-01-01"


@pytest.mark.unit
def test_calendar_yfinance_fallback_does_not_recurse(cache, monkeypatch):
    monkeypatch.setattr(earnings_data, "_finnhub_calendar", lambda start, end, tickers: [])
    monkeypatch.setattr(earnings_data, "_yfinance_next_earnings", lambda ticker: earnings_data.EarningsEvent(ticker=ticker, report_date="2026-02-01"))
    events = earnings_data.get_earnings_calendar(start_date="2026-01-01", end_date="2026-03-01", tickers=["AAPL"])
    assert events[0].report_date == "2026-02-01"


@pytest.mark.unit
def test_next_earnings_handles_none_dates(cache, monkeypatch):
    monkeypatch.setattr(earnings_data, "_finnhub_calendar", lambda start, end, tickers: [earnings_data.EarningsEvent(ticker="AAPL", report_date=None)])
    monkeypatch.setattr(earnings_data, "_yfinance_next_earnings", lambda ticker: None)
    assert earnings_data.get_next_earnings("AAPL") is None


@pytest.mark.unit
def test_surprise_stats(cache, monkeypatch):
    monkeypatch.setattr(
        earnings_data,
        "get_earnings_history",
        lambda ticker, limit=8: [
            earnings_data.EarningsSurprise(ticker=ticker, beat_miss="beat", surprise_pct=10),
            earnings_data.EarningsSurprise(ticker=ticker, beat_miss="miss", surprise_pct=-5),
        ],
    )
    stats = earnings_data.get_earnings_surprise_stats("AAPL")
    assert stats.beat_rate == 0.5
    assert stats.average_surprise_pct == 2.5


@pytest.mark.unit
def test_surprise_stats_zero_history(cache, monkeypatch):
    monkeypatch.setattr(earnings_data, "get_earnings_history", lambda ticker, limit=8: [])
    stats = earnings_data.get_earnings_surprise_stats("AAPL")
    assert stats.quarters == 0
    assert stats.warnings

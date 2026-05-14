import time

import pytest

from tradingagents.infra.cache.sqlite import SQLiteCache


@pytest.mark.unit
def test_sqlite_cache_round_trip_and_expiry(tmp_path):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    assert cache.set("quotes", "AAPL", {"price": 123}, ttl_seconds=1)
    assert cache.get("quotes", "AAPL") == {"price": 123}
    time.sleep(1.1)
    assert cache.get("quotes", "AAPL") is None
    assert cache.get_stale("quotes", "AAPL") == {"price": 123}


@pytest.mark.unit
def test_sqlite_cache_failure_is_safe(tmp_path):
    cache = SQLiteCache(tmp_path)
    assert cache.get("quotes", "AAPL") is None
    assert cache.set("quotes", "AAPL", {"price": 123}, ttl_seconds=1) is False

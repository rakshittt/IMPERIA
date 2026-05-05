import pytest

from tradingagents.persistence import db as db_module
from tradingagents.persistence.db import PersistenceDB
from tradingagents.persistence import portfolio, watchlist
from tradingagents.dataflows.market_data import QuoteData


@pytest.fixture()
def persistence_db(tmp_path, monkeypatch):
    test_db = PersistenceDB(tmp_path / "user_data.db")
    monkeypatch.setattr(db_module, "_DB", test_db)
    return test_db


@pytest.mark.unit
def test_db_initializes_tables(persistence_db):
    persistence_db.initialize()
    rows = persistence_db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
    assert {"watchlists", "portfolio_snapshots", "research_results"}.issubset({row["name"] for row in rows})


@pytest.mark.unit
def test_watchlist_crud(persistence_db):
    record = watchlist.create_watchlist("Core", ["aapl", "msft", "AAPL"])
    assert record.tickers == ["AAPL", "MSFT"]
    updated = watchlist.add_ticker_to_watchlist(record.id, "nvda")
    assert "NVDA" in updated.tickers
    removed = watchlist.remove_ticker_from_watchlist(record.id, "msft")
    assert "MSFT" not in removed.tickers
    assert watchlist.delete_watchlist(record.id) is True


@pytest.mark.unit
def test_watchlist_quotes(persistence_db, monkeypatch):
    record = watchlist.create_watchlist("Core", ["AAPL"])
    monkeypatch.setattr(watchlist, "get_batch_quotes", lambda tickers: {"AAPL": QuoteData(ticker="AAPL", price=1)})
    assert watchlist.get_watchlist_quotes(record.id)[0].price == 1


@pytest.mark.unit
def test_portfolio_snapshots(persistence_db):
    saved = portfolio.save_portfolio_snapshot({"aapl": 0.6, "msft": 0.4}, "Growth")
    assert portfolio.get_portfolio_snapshot(saved.id).holdings["AAPL"] == 0.6
    assert portfolio.list_portfolio_snapshots()[0].label == "Growth"


@pytest.mark.unit
def test_research_persistence(persistence_db):
    assert portfolio.persist_research_result("r1", {"answer": "ok"}, status="completed")
    persisted = portfolio.get_persisted_research("r1")
    assert persisted["result"]["answer"] == "ok"
    portfolio.update_research_status("r1", "failed", error="boom")
    assert portfolio.list_research_results()[0].status == "failed"

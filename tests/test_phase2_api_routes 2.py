import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.api.routes import earnings, market, research, screener, stock, watchlist
from tradingagents.dataflows.screener import ScreenerCriteria, ScreenerResult


class Dumpable:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_API_CACHE_TTL", "0")
    monkeypatch.setattr(market.market_data, "get_market_breadth", lambda: Dumpable({"advancing": 2, "declining": 1, "unchanged": 0, "total": 3}))
    monkeypatch.setattr(market.market_data, "get_sector_performance", lambda: [Dumpable({"sector": "Technology", "ticker": "XLK"})])
    monkeypatch.setattr(market.market_data, "get_market_indices", lambda: [Dumpable({"ticker": "SPY", "price": 500})])
    monkeypatch.setattr(market.market_data, "get_market_movers", lambda n=10: Dumpable({"gainers": [{"ticker": "AAA"}], "losers": []}))
    monkeypatch.setattr(market.news_aggregator, "get_market_news", lambda limit=5: [Dumpable({"title": "Market news"})])

    monkeypatch.setattr(stock.market_data, "get_intraday", lambda ticker, interval="5m": None)
    monkeypatch.setattr(stock.market_data, "ohlcv_to_records", lambda frame: [{"close": 1.0}])
    monkeypatch.setattr(stock.earnings_data, "get_next_earnings", lambda ticker: Dumpable({"ticker": ticker.upper(), "report_date": "2026-02-01"}))

    monkeypatch.setattr(earnings.earnings_data, "get_earnings_calendar", lambda start_date=None, end_date=None, tickers=None: [Dumpable({"ticker": "AAPL", "report_date": "2026-02-01"})])
    monkeypatch.setattr(earnings.earnings_data, "get_earnings_history", lambda ticker, limit=8: [Dumpable({"ticker": ticker.upper(), "beat_miss": "beat"})])
    monkeypatch.setattr(earnings.earnings_data, "get_next_earnings", lambda ticker: Dumpable({"ticker": ticker.upper(), "report_date": "2026-02-01"}))

    monkeypatch.setattr(screener, "screen_stocks", lambda criteria: [ScreenerResult(ticker="AAPL", market_cap=1)])
    monkeypatch.setattr(screener, "parse_nl_screener_query", lambda query: ScreenerCriteria() if "things" in query else ScreenerCriteria(max_pe=20))

    monkeypatch.setattr(watchlist, "create_watchlist", lambda name, tickers: Dumpable({"id": "wl1", "name": name, "tickers": tickers}))
    monkeypatch.setattr(watchlist, "list_watchlists", lambda: [Dumpable({"id": "wl1", "name": "Tech", "tickers": ["AAPL"]})])
    monkeypatch.setattr(watchlist, "get_watchlist", lambda watchlist_id: Dumpable({"id": watchlist_id, "name": "Tech", "tickers": ["AAPL"]}))
    monkeypatch.setattr(watchlist, "add_ticker_to_watchlist", lambda watchlist_id, ticker: Dumpable({"id": watchlist_id, "name": "Tech", "tickers": ["AAPL", ticker]}))
    monkeypatch.setattr(watchlist, "remove_ticker_from_watchlist", lambda watchlist_id, ticker: Dumpable({"id": watchlist_id, "name": "Tech", "tickers": []}))
    monkeypatch.setattr(watchlist, "delete_watchlist", lambda watchlist_id: True)
    monkeypatch.setattr(watchlist, "get_watchlist_quotes", lambda watchlist_id: [Dumpable({"ticker": "AAPL", "price": 1})])

    monkeypatch.setattr(research, "submit_research_job", lambda runner, portfolio, analysis_date, profile: {"research_id": "r1", "status": "queued"})
    monkeypatch.setattr(research, "list_research_results", lambda limit=20: [Dumpable({"id": "r1", "status": "completed"})])
    monkeypatch.setattr(research, "get_persisted_research", lambda research_id: {"id": research_id, "status": "completed", "result": {}})
    return TestClient(create_app())


@pytest.mark.unit
def test_phase2_market_routes(client):
    assert client.get("/api/market/breadth").json()["advancing"] == 2
    assert client.get("/api/market/sectors").json()[0]["ticker"] == "XLK"
    assert client.get("/api/market/summary").json()["top_news"][0]["title"] == "Market news"


@pytest.mark.unit
def test_phase2_stock_routes(client):
    assert client.get("/api/stock/AAPL/intraday").json()["points"][0]["close"] == 1.0
    assert client.get("/api/stock/AAPL/next-earnings").json()["report_date"] == "2026-02-01"


@pytest.mark.unit
def test_phase2_earnings_routes(client):
    assert client.get("/api/earnings/calendar?tickers=AAPL").json()[0]["ticker"] == "AAPL"
    assert client.get("/api/earnings/AAPL/history").json()[0]["beat_miss"] == "beat"
    assert client.get("/api/earnings/AAPL/next").json()["report_date"] == "2026-02-01"


@pytest.mark.unit
def test_phase2_screener_routes(client):
    assert client.post("/api/screener/run", json={"max_pe": 20}).json()["results"][0]["ticker"] == "AAPL"
    assert client.post("/api/screener/nl", json={"query": "cheap tech stocks"}).json()["criteria"]["max_pe"] == 20


@pytest.mark.unit
def test_phase3_validation_routes(client):
    assert client.get("/api/stock/BTC-USD/profile").status_code == 422
    assert client.get("/api/earnings/AAPL/history?limit=0").status_code == 422
    assert client.post("/api/screener/nl", json={"query": "show me things"}).status_code == 422


@pytest.mark.unit
def test_phase2_watchlist_routes(client):
    assert client.post("/api/watchlist", json={"name": "Tech", "tickers": ["AAPL"]}).json()["id"] == "wl1"
    assert client.get("/api/watchlist").json()[0]["name"] == "Tech"
    assert client.post("/api/watchlist/wl1/tickers", json={"ticker": "MSFT"}).json()["tickers"][-1] == "MSFT"
    assert client.get("/api/watchlist/wl1/quotes").json()[0]["ticker"] == "AAPL"
    assert client.delete("/api/watchlist/wl1").json()["deleted"] is True


@pytest.mark.unit
def test_phase2_research_routes(client):
    assert client.post("/api/research", json={"portfolio": [{"ticker": "AAPL", "weight": 1}]}).json()["status"] == "queued"
    assert client.get("/api/research").json()[0]["id"] == "r1"
    assert client.get("/api/research/r1").json()["status"] == "completed"

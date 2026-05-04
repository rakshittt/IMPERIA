import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.api.routes import ai, market, search, stock


class FakeEngine:
    def search(self, q, limit=10):
        return [{"ticker": "AAPL", "name": "Apple Inc.", "supported": True}]

    def get_profile(self, ticker):
        return {"ticker": ticker.upper(), "name": "Apple Inc."}

    def get_financials(self, ticker):
        return {"ticker": ticker.upper(), "computed": {"metrics": {"pe": 10}}}

    def get_ratios(self, ticker):
        return {"ticker": ticker.upper(), "metrics": {"pe": 10}}

    def get_chart(self, ticker, period="1mo", interval="1d"):
        return {"ticker": ticker.upper(), "points": []}

    def get_news(self, ticker, limit=10):
        return [{"title": "Headline", "url": "https://example.com"}]

    def get_earnings(self, ticker):
        return {"ticker": ticker.upper(), "earnings_dates": []}

    def get_holders(self, ticker):
        return {"ticker": ticker.upper(), "institutional_holders": []}

    def get_market_indices(self):
        return [{"name": "S&P 500", "symbol": "^GSPC", "price": 5000, "change_pct": 1}]

    def get_market_movers(self, limit=10):
        return {"gainers": [{"ticker": "AAPL"}], "losers": []}

    def get_market_summary(self):
        return {"indices": self.get_market_indices(), "movers": self.get_market_movers()}

    def answer_query(self, query):
        return {"mode": "fast", "answer": "AAPL summary", "key_stats": {}, "data": {}, "citations": [], "warnings": []}


@pytest.fixture()
def client(monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr(search, "get_fast_engine", lambda: fake)
    monkeypatch.setattr(stock, "get_fast_engine", lambda: fake)
    monkeypatch.setattr(market, "get_fast_engine", lambda: fake)
    monkeypatch.setattr(ai, "get_fast_engine", lambda: fake)
    return TestClient(create_app())


@pytest.mark.unit
def test_core_api_endpoints(client):
    assert client.get("/api/search?q=apple").json()["results"][0]["ticker"] == "AAPL"
    assert client.get("/api/stock/AAPL/profile").json()["name"] == "Apple Inc."
    assert client.get("/api/stock/AAPL/financials").json()["computed"]["metrics"]["pe"] == 10
    assert client.get("/api/stock/AAPL/ratios").json()["metrics"]["pe"] == 10
    assert client.get("/api/stock/AAPL/news").json()["articles"][0]["title"] == "Headline"
    assert client.get("/api/stock/AAPL/earnings").json()["earnings_dates"] == []
    assert client.get("/api/stock/AAPL/holders").json()["institutional_holders"] == []
    assert client.get("/api/market/indices").json()[0]["symbol"] == "^GSPC"
    assert client.get("/api/market/movers").json()["gainers"][0]["ticker"] == "AAPL"
    assert client.get("/api/market/summary").json()["indices"][0]["name"] == "S&P 500"


@pytest.mark.unit
def test_ask_and_research_compat(client, monkeypatch):
    assert client.post("/api/ask", json={"query": "What is Apple P/E?"}).json()["mode"] == "fast"

    def fake_research(portfolio, analysis_date=None, profile=None):
        return {
            "id": "abc123",
            "market_report": "Market",
            "final_portfolio_feedback": "Feedback",
        }

    monkeypatch.setattr(ai, "run_deep_research", fake_research)
    response = client.post(
        "/api/analyze",
        json={"portfolio": [{"ticker": "AAPL", "weight": 1.0}], "profile": {}},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "abc123"

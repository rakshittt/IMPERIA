import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.api.routes import research
from tradingagents.dataflows import demo_provider, news_aggregator, polymarket_sentiment


@pytest.fixture()
def demo_client(monkeypatch, tmp_path):
    monkeypatch.setenv("IMPERIA_DEMO_MODE", "true")
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("PERSISTENCE_DB_PATH", str(tmp_path / "user.sqlite3"))
    return TestClient(create_app())


@pytest.mark.unit
def test_demo_universe_has_deterministic_core_fixtures(monkeypatch):
    monkeypatch.setenv("IMPERIA_DEMO_MODE", "true")
    universe = demo_provider.demo_universe()
    assert len(universe) >= 100
    for ticker in universe:
        assert demo_provider.get_demo_quote(ticker)["ticker"] == ticker
        assert demo_provider.get_demo_profile(ticker)["ticker"] == ticker
        assert demo_provider.get_demo_metrics(ticker)["ticker"] == ticker
        assert demo_provider.get_demo_earnings(ticker)["next"]["ticker"] == ticker
        assert demo_provider.get_demo_filings(ticker, limit=1)[0]["ticker"] == ticker
        assert demo_provider.get_demo_sentiment(ticker)["ticker"] == ticker


@pytest.mark.unit
def test_stock_first_ask_needs_no_portfolio_and_reframes_advice(demo_client):
    response = demo_client.post("/api/ask", json={"ticker": "NVDA", "query": "Should I buy NVDA?"})
    payload = response.json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["mode"] == "fast"
    assert payload["ticker"] == "NVDA"
    assert "cannot tell you whether to buy" in payload["answer"]
    assert "you should buy" not in payload["answer"].lower()
    assert payload["metadata"]["not_investment_advice"] is True


@pytest.mark.unit
def test_ticker_only_research_submission_needs_no_portfolio(demo_client, monkeypatch):
    monkeypatch.setattr(research, "submit_research_job", lambda runner, portfolio, analysis_date, profile: {"research_id": "stock1", "status": "queued"})
    response = demo_client.post("/api/research", json={"ticker": "AAPL", "question": "Analyze Apple earnings."})
    assert response.status_code == 200
    assert response.json()["research_id"] == "stock1"


@pytest.mark.unit
def test_news_window_aliases_and_default_today(demo_client):
    assert news_aggregator.normalize_news_window("1d") == "past_day"
    assert news_aggregator.normalize_news_window("7d") == "past_week"
    payload = demo_client.get("/api/stock/AAPL/news").json()
    assert payload["window"] == "today"
    assert payload["articles"][0]["ticker" if "ticker" in payload["articles"][0] else "tickers"][0] == "AAPL"
    assert payload["citations"]


@pytest.mark.unit
def test_polymarket_disabled_by_default(monkeypatch):
    monkeypatch.delenv("IMPERIA_DEMO_MODE", raising=False)
    monkeypatch.delenv("IMPERIA_ENABLE_POLYMARKET", raising=False)
    result = polymarket_sentiment.get_polymarket_sentiment("NVDA")
    assert result.sentiment_label == "uncertain"
    assert "disabled" in result.warnings[0].lower()


@pytest.mark.unit
def test_polymarket_enabled_no_market_found(monkeypatch, tmp_path):
    monkeypatch.delenv("IMPERIA_DEMO_MODE", raising=False)
    monkeypatch.setenv("IMPERIA_ENABLE_POLYMARKET", "true")
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setattr(polymarket_sentiment, "safe_get_json", lambda *args, **kwargs: {"markets": []})
    result = polymarket_sentiment.get_polymarket_sentiment("NVDA", "NVIDIA Corporation")
    assert result.sentiment_label == "uncertain"
    assert result.confidence_score == 0
    assert "No sufficiently relevant" in result.warnings[-1]


@pytest.mark.unit
def test_sentiment_endpoint_shape_and_no_direct_advice(demo_client):
    payload = demo_client.get("/api/stock/NVDA/sentiment").json()
    assert payload["success"] is True
    assert payload["data"]["sentiment_label"] in {"bullish", "neutral", "bearish", "mixed", "uncertain"}
    rendered = str(payload).lower()
    assert "you should buy" not in rendered
    assert "recommendation" not in payload["data"]
    assert payload["metadata"]["not_investment_advice"] is True


@pytest.mark.unit
def test_stock_first_research_endpoints(demo_client):
    paths = [
        "/api/stock/AAPL/what-happened",
        "/api/stock/AAPL/research-snapshot",
        "/api/stock/AAPL/risks",
        "/api/stock/AAPL/bull-bear",
        "/api/stock/AAPL/earnings-brief",
        "/api/stock/AAPL/filing-brief",
        "/api/stock/AAPL/investor-checklist",
    ]
    for path in paths:
        payload = demo_client.get(path).json()
        assert payload["success"] is True
        assert payload["metadata"]["not_investment_advice"] is True


@pytest.mark.unit
def test_compare_two_stocks_endpoint(demo_client):
    payload = demo_client.get("/api/compare?ticker_a=AMD&ticker_b=NVDA").json()
    assert payload["success"] is True
    assert payload["data"]["ticker_a"] == "AMD"
    assert payload["data"]["ticker_b"] == "NVDA"
    assert "valuation_comparison" in payload["data"]


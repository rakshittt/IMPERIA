import itertools
import time

import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.infra.cache.redis import redis_status
from tradingagents.dataflows import analyst_consensus, form4_parser, fred_macro, peer_comparison, thirteen_f_parser
from tradingagents.core.intelligence import stock as stock_intelligence
from tradingagents.persistence import db as db_module
from tradingagents.persistence.db import PersistenceDB
from tradingagents.workers import background_jobs


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSISTENCE_DB_PATH", str(tmp_path / "user.db"))
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("TRADINGAGENTS_API_CACHE_TTL", "0")
    monkeypatch.setattr(db_module, "_DB", PersistenceDB(tmp_path / "user.db"))
    return TestClient(create_app())


@pytest.mark.unit
def test_fred_macro_missing_key_degrades(monkeypatch, tmp_path):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("IMPERIA_DEMO_MODE", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    result = fred_macro.get_macro_indicators()
    assert result.indicators == {}
    assert "FRED_API_KEY" in result.warnings[0]


@pytest.mark.unit
def test_form4_parser_no_data(monkeypatch):
    monkeypatch.setattr(form4_parser, "get_form4_insider_trades", lambda ticker, limit=50: [])
    result = form4_parser.get_form4_activity("AAPL")
    assert result.transactions == []
    assert "No recent Form 4" in result.warnings[-1]


@pytest.mark.unit
def test_thirteen_f_parser_no_data(monkeypatch):
    monkeypatch.setattr(thirteen_f_parser, "get_13f_related_filings", lambda ticker, limit=50: {"ticker": ticker, "filings": [], "limitation": "lagged"})
    result = thirteen_f_parser.get_thirteen_f_activity("AAPL")
    assert result.filings == []
    assert result.limitation == "lagged"
    assert "No issuer-related 13F" in result.warnings[-1]


@pytest.mark.unit
def test_analyst_consensus_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("IMPERIA_DEMO_MODE", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    result = analyst_consensus.get_analyst_consensus("AAPL")
    assert result.buy_count is None
    assert "FINNHUB_API_KEY" in result.warnings[0]


@pytest.mark.unit
def test_peer_comparison_module_with_mocked_sources(monkeypatch):
    class Quote:
        change_pct = 1.2
        market_cap = 100
        source = "mock"

    monkeypatch.setattr(peer_comparison.market_data, "get_quote", lambda ticker: Quote())
    monkeypatch.setattr(peer_comparison, "compute_financial_metrics", lambda ticker: {"metrics": {"pe": 10, "revenue_growth": 0.1, "net_margin": 0.2, "roe": 0.3}})
    result = peer_comparison.get_peer_comparison("AAPL", limit=2)
    assert len(result.peers) == 2
    assert result.citations


@pytest.mark.unit
def test_provider_health_reports_required_modules(client):
    payload = client.get("/api/health/providers").json()
    for key in [
        "redis_status",
        "fred_status",
        "polymarket_status",
        "form4_parser_status",
        "thirteen_f_parser_status",
        "analyst_consensus_status",
        "peer_comparison_status",
        "institutional_holder_status",
        "research_streaming_status",
        "llm_usage_tracking_status",
        "admin_api_status",
        "portfolio_snapshot_status",
    ]:
        assert key in payload


@pytest.mark.unit
def test_admin_api_endpoints_exist(client):
    for path in ["/api/admin/status", "/api/admin/providers", "/api/admin/cache", "/api/admin/research-jobs", "/api/admin/agent-runs", "/api/admin/agent-methodology", "/api/admin/llm-usage", "/api/admin/cost", "/api/admin/errors", "/api/health/llm"]:
        response = client.get(path)
        assert response.status_code == 200


@pytest.mark.unit
def test_portfolio_snapshot_crud(client):
    created = client.post("/api/portfolio/snapshots", json={"label": "Demo", "holdings": {"AAPL": 0.6, "MSFT": 0.4}}).json()
    snapshot_id = created["data"]["id"]
    assert client.get("/api/portfolio/snapshots").json()["data"]["snapshots"][0]["id"] == snapshot_id
    assert client.get(f"/api/portfolio/snapshots/{snapshot_id}").json()["data"]["holdings"]["AAPL"] == 0.6
    assert client.delete(f"/api/portfolio/snapshots/{snapshot_id}").json()["data"]["deleted"] is True
    assert client.get(f"/api/portfolio/snapshots/{snapshot_id}").status_code == 404


@pytest.mark.unit
def test_research_streaming_events_buffer():
    rid = f"r{int(time.time() * 1000)}"
    background_jobs.emit_research_event(rid, "agent_completed", agent="News & Event Analyst", warnings=[])
    events = background_jobs.research_events(rid)
    assert events[-1]["event"] == "agent_completed"
    assert events[-1]["agent"] == "News & Event Analyst"


@pytest.mark.unit
def test_redis_status_graceful_when_unavailable(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1")
    status = redis_status()
    assert {"configured", "available", "backend", "error"}.issubset(status)


@pytest.mark.unit
def test_research_job_lifecycle_events(monkeypatch, tmp_path):
    monkeypatch.setattr(db_module, "_DB", PersistenceDB(tmp_path / "jobs.db"))
    ids = itertools.count()

    def runner(portfolio, analysis_date, profile, research_id):
        background_jobs.emit_research_event(research_id, "agent_started", agent="fundamentals")
        return {"id": research_id, "ok": next(ids) >= 0}

    job = background_jobs.submit_research_job(runner, [{"ticker": "AAPL"}], None, {}, research_id="expertjob")
    for _ in range(20):
        status = background_jobs.get_research_job(job["research_id"])
        if status and status["status"] == "completed":
            break
        time.sleep(0.05)
    events = [event["event"] for event in background_jobs.research_events("expertjob")]
    assert "queued" in events
    assert "running" in events
    assert "agent_started" in events
    assert "completed" in events


@pytest.mark.unit
def test_compare_stocks_degrades_when_sec_filings_fail(monkeypatch):
    monkeypatch.setattr(stock_intelligence, "compute_financial_metrics", lambda ticker: {"metrics": {"pe": 10}, "warnings": [], "citations": []})
    monkeypatch.setattr(stock_intelligence, "get_stock_sentiment", lambda ticker: type("Sentiment", (), {"model_dump": lambda self: {"sentiment_label": "neutral", "warnings": [], "citations": []}})())
    monkeypatch.setattr(stock_intelligence, "get_sec_filings", lambda ticker, limit=5: (_ for _ in ()).throw(ValueError("missing cik")))
    payload = stock_intelligence.compare_stocks("AMD", "NVDA")
    assert payload["ticker_a"] == "AMD"
    assert payload["ticker_b"] == "NVDA"
    assert any("SEC filings unavailable" in warning for warning in payload["warnings"])

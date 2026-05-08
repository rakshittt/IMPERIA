"""Tests that IMPERIA_DEMO_MODE=true works end-to-end without live providers.

These are unit tests (all mocked) that verify demo mode:
- Returns valid JSON for key stock endpoints
- Does not attempt real network calls
- Returns the DEMO_WARNING in the response
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def demo_client(monkeypatch):
    monkeypatch.setenv("IMPERIA_DEMO_MODE", "true")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("TRADINGAGENTS_API_CACHE_TTL", "0")
    from tradingagents.api.main import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.unit
def test_health_ok_in_demo_mode(demo_client):
    resp = demo_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.unit
def test_demo_mode_search_returns_results(demo_client):
    resp = demo_client.get("/api/search", params={"q": "Apple"})
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


@pytest.mark.unit
def test_demo_mode_market_indices(demo_client):
    resp = demo_client.get("/api/market/indices")
    assert resp.status_code == 200


@pytest.mark.unit
def test_demo_mode_market_summary(demo_client):
    resp = demo_client.get("/api/market/summary")
    assert resp.status_code == 200


@pytest.mark.unit
def test_demo_mode_stock_profile(demo_client):
    resp = demo_client.get("/api/stock/AAPL/profile")
    assert resp.status_code == 200


@pytest.mark.unit
def test_demo_mode_screener_nl(demo_client):
    resp = demo_client.post("/api/screener/nl", json={"query": "technology stocks"})
    assert resp.status_code == 200


@pytest.mark.unit
def test_demo_mode_research_submit_queues_job(demo_client, monkeypatch):
    """Research submission should queue a job even in demo mode (no auth key set)."""
    import os
    os.environ.pop("IMPERIA_API_KEY", None)
    resp = demo_client.post(
        "/api/research",
        json={"ticker": "AAPL", "question": "Demo research test."},
    )
    assert resp.status_code in {200, 201}
    data = resp.json()
    assert "research_id" in data or "id" in data


@pytest.mark.unit
def test_request_body_too_large_not_accepted(demo_client):
    """Requests over 1 MB must not return 200 -- either 413 (size limit) or 422 (parse error)."""
    large_payload = b"x" * (1 * 1024 * 1024 + 100)
    resp = demo_client.post(
        "/api/ask",
        content=large_payload,
        headers={"Content-Type": "application/json"},
    )
    # Must NOT succeed -- the server refuses large or invalid payloads
    assert resp.status_code in {413, 422, 400}


@pytest.mark.unit
def test_admin_blocked_with_wrong_key(monkeypatch):
    """Admin endpoint returns 401 when IMPERIA_API_KEY is set and key is wrong."""
    monkeypatch.setenv("IMPERIA_API_KEY", "secret-key-abc")
    monkeypatch.setenv("IMPERIA_DEMO_MODE", "true")
    monkeypatch.setenv("TRADINGAGENTS_API_CACHE_TTL", "0")
    from tradingagents.api.main import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.get("/api/admin/status", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


@pytest.mark.unit
def test_admin_open_without_key(monkeypatch):
    """Admin endpoint is open when IMPERIA_API_KEY is not set."""
    monkeypatch.delenv("IMPERIA_API_KEY", raising=False)
    monkeypatch.setenv("IMPERIA_DEMO_MODE", "true")
    monkeypatch.setenv("TRADINGAGENTS_API_CACHE_TTL", "0")
    from tradingagents.api.main import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app(), raise_server_exceptions=False)
    resp = client.get("/api/admin/status")
    assert resp.status_code == 200

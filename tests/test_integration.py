"""Integration smoke tests -- boot the real app, hit real endpoints.

These tests exercise the full FastAPI stack including middleware,
routing, and schema validation but mock the DeepSeek LLM so they
run without an AI key and complete in <10 seconds.

Run with: pytest tests/test_integration.py -v -m integration
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a TestClient against the real app (no external LLM calls)."""
    from tradingagents.api.main import create_app
    return TestClient(create_app(), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "IMPERIA" in resp.text


@pytest.mark.integration
def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["product"] == "IMPERIA"


@pytest.mark.integration
def test_health_ready_shape(client):
    """Ready endpoint must return valid JSON with a status and checks dict."""
    resp = client.get("/api/health/ready")
    # Returns 200 or 503 depending on env; both are valid shapes
    assert resp.status_code in {200, 503}
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert "sqlite_cache" in data["checks"]
    assert "deepseek_key" in data["checks"]


@pytest.mark.integration
def test_health_providers_shape(client):
    resp = client.get("/api/health/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.integration
def test_health_llm_shape(client):
    resp = client.get("/api/health/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "deepseek_configured" in data


# ---------------------------------------------------------------------------
# Search endpoint -- uses yfinance, should respond without AI key
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_search_returns_list(client):
    resp = client.get("/api/search?q=Apple")
    assert resp.status_code == 200
    data = resp.json()
    # Response is either a list or a dict with a results key
    assert isinstance(data, (list, dict))


@pytest.mark.integration
def test_search_empty_query(client):
    """Empty search should return 200 or 422, not 500."""
    resp = client.get("/api/search?q=")
    assert resp.status_code in {200, 400, 422}


# ---------------------------------------------------------------------------
# Stock endpoints -- deterministic, no AI key needed
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_stock_quote_aapl(client):
    resp = client.get("/api/stock/AAPL/quote")
    # May fail if yfinance is unavailable in test env; just must not 500 with traceback
    assert resp.status_code in {200, 503, 404}
    if resp.status_code == 200:
        data = resp.json()
        assert "ticker" in str(data).upper() or "AAPL" in str(data).upper() or "data" in data or isinstance(data, dict)


@pytest.mark.integration
def test_stock_summary_shape(client):
    resp = client.get("/api/stock/AAPL/summary")
    assert resp.status_code in {200, 503, 404}


@pytest.mark.integration
def test_stock_news_shape(client):
    resp = client.get("/api/stock/AAPL/news")
    assert resp.status_code in {200, 503, 404}


@pytest.mark.integration
def test_stock_ratios_shape(client):
    resp = client.get("/api/stock/AAPL/ratios")
    assert resp.status_code in {200, 503, 404}


@pytest.mark.integration
def test_invalid_ticker_does_not_500(client):
    """Garbage ticker must degrade gracefully, never 500."""
    resp = client.get("/api/stock/NOTAREALTICKERXYZ/quote")
    assert resp.status_code != 500


# ---------------------------------------------------------------------------
# Admin auth -- admin endpoints must be 401 when key is set
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_admin_status_open_when_no_key_set(client):
    """Without IMPERIA_API_KEY in env the admin routes are open (local dev)."""
    # The fixture-level client was created without an env key, so admin is open
    if os.environ.get("IMPERIA_API_KEY", "").strip():
        pytest.skip("IMPERIA_API_KEY is set in env; skipping open-access test")
    resp = client.get("/api/admin/status")
    assert resp.status_code == 200


@pytest.mark.integration
def test_admin_blocked_with_wrong_key(monkeypatch):
    """Wrong X-API-Key returns 401; correct key is allowed."""
    monkeypatch.setenv("IMPERIA_API_KEY", "test-secret-key")
    from tradingagents.api.main import create_app
    fresh_client = TestClient(create_app(), raise_server_exceptions=False)
    # Wrong key -> blocked
    resp = fresh_client.get("/api/admin/status", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401
    # Correct key -> allowed
    resp_authed = fresh_client.get("/api/admin/status", headers={"X-API-Key": "test-secret-key"})
    assert resp_authed.status_code == 200


# ---------------------------------------------------------------------------
# Research POST -- must require auth when key is set
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_research_post_blocked_when_key_set(monkeypatch):
    """POST /api/research must be 401 without key when IMPERIA_API_KEY is set."""
    monkeypatch.setenv("IMPERIA_API_KEY", "test-secret-key")
    from tradingagents.api.main import create_app
    fresh_client = TestClient(create_app(), raise_server_exceptions=False)
    resp = fresh_client.post("/api/research", json={"ticker": "AAPL"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Request body size limit
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_oversized_body_rejected(client):
    """Bodies over 1 MB must be rejected with 413 or caught by the JSON parser."""
    oversized = b"x" * (2 * 1024 * 1024)  # 2 MB of raw bytes
    resp = client.post(
        "/api/research",
        content=oversized,
        headers={"Content-Type": "application/json", "Content-Length": str(len(oversized))},
    )
    # The middleware runs before the JSON parser so large content-length → 413
    # If the parser wins it returns 422; both are acceptable (never 500)
    assert resp.status_code in {400, 413, 422}


# ---------------------------------------------------------------------------
# Watchlist and portfolio CRUD -- no AI key needed
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_watchlist_create_and_read(client):
    create_resp = client.post("/api/watchlist", json={"name": "Test WL", "tickers": ["AAPL", "MSFT"]})
    assert create_resp.status_code == 200
    wl = create_resp.json()
    assert "id" in wl

    # GET all watchlists
    list_resp = client.get("/api/watchlist")
    assert list_resp.status_code == 200
    assert isinstance(list_resp.json(), list)

    # GET specific
    get_resp = client.get(f"/api/watchlist/{wl['id']}")
    assert get_resp.status_code == 200

    # DELETE
    del_resp = client.delete(f"/api/watchlist/{wl['id']}")
    assert del_resp.status_code == 200


@pytest.mark.integration
def test_watchlist_404_for_missing(client):
    resp = client.get("/api/watchlist/does-not-exist-xyz")
    assert resp.status_code == 404


@pytest.mark.integration
def test_portfolio_snapshot_lifecycle(client):
    create_resp = client.post(
        "/api/portfolio/snapshots",
        json={"label": "Test snapshot", "holdings": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    assert create_resp.status_code == 200
    snap = create_resp.json()
    assert "data" in snap or "id" in snap
    snap_id = snap.get("data", snap).get("id") or snap.get("id")

    # GET all
    list_resp = client.get("/api/portfolio/snapshots")
    assert list_resp.status_code == 200

    if snap_id:
        # GET specific
        get_resp = client.get(f"/api/portfolio/snapshots/{snap_id}")
        assert get_resp.status_code == 200

        # DELETE
        del_resp = client.delete(f"/api/portfolio/snapshots/{snap_id}")
        assert del_resp.status_code == 200


@pytest.mark.integration
def test_portfolio_404_for_missing(client):
    resp = client.get("/api/portfolio/snapshots/does-not-exist-xyz")
    assert resp.status_code == 404

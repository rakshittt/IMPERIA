import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tradingagents.api.middleware.rate_limiter import RateLimitMiddleware
from tradingagents.api.middleware.security import SecurityHeadersMiddleware


@pytest.mark.unit
def test_rate_limiter_returns_retry_after():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60)

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/api/ping").status_code == 200
    response = client.get("/api/ping")
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.unit
def test_security_headers_added():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/ping")
    async def ping():
        return {"ok": True}

    response = TestClient(app).get("/api/ping")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.unit
def test_security_middleware_hides_stack_trace():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/fail")
    async def fail():
        raise RuntimeError("secret failure")

    response = TestClient(app, raise_server_exceptions=False).get("/api/fail")
    assert response.status_code == 500
    assert "secret failure" not in response.text

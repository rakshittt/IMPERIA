from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from tradingagents.api.middleware.cache_middleware import CacheMiddleware
from tradingagents.api.middleware.rate_limiter import RateLimitMiddleware
from tradingagents.api.middleware.request_id import RequestIDMiddleware
from tradingagents.api.middleware.security import SecurityHeadersMiddleware
from tradingagents.api.routes import admin, ai, earnings, market, portfolio, research, screener, search, stock, watchlist
from tradingagents.providers.registry import configured_provider_status
from tradingagents.infra.llm.deepseek import deepseek_model_status

load_dotenv()

_MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024  # 1 MB hard limit on request bodies


def create_app() -> FastAPI:
    app = FastAPI(
        title="IMPERIA Finance Intelligence API",
        description="Backend-first US equity intelligence engine with fast answers and deep multi-agent research.",
        version="0.3.0",
    )

    # Restrict CORS: default to localhost only so the wildcard is never
    # accidentally shipped to production. Set TRADINGAGENTS_CORS_ORIGINS to a
    # comma-separated list of allowed origins in production.
    _raw_origins = os.getenv("TRADINGAGENTS_CORS_ORIGINS", "").strip()
    _origins = (
        [o.strip() for o in _raw_origins.split(",") if o.strip()]
        if _raw_origins
        else ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CacheMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.middleware("http")
    async def limit_request_body(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_REQUEST_BODY_BYTES:
            return JSONResponse(
                {"error": "request_too_large", "detail": "Request body exceeds 1 MB limit."},
                status_code=413,
            )
        return await call_next(request)

    app.include_router(search.router)
    app.include_router(stock.router)
    app.include_router(stock.compat_router)
    app.include_router(market.router)
    app.include_router(market.compat_router)
    app.include_router(earnings.router)
    app.include_router(screener.router)
    app.include_router(watchlist.router)
    app.include_router(portfolio.router)
    app.include_router(research.router)
    app.include_router(ai.router)
    app.include_router(admin.router)

    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        return "<html><body><h1>IMPERIA API</h1><p>US equity intelligence backend is running.</p></body></html>"

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "product": "IMPERIA",
            "tagline": "Source-cited AI research for US stocks.",
            "scope": "US equities and major US ETFs, free/open data sources",
        }

    @app.get("/api/health/ready")
    async def health_ready():
        """Readiness probe: verifies SQLite cache is writable and DeepSeek key is present."""
        checks: dict[str, str] = {}
        overall = "ok"

        try:
            from tradingagents.infra.cache.sqlite import get_default_cache
            cache = get_default_cache()
            cache.set("health", "__healthcheck__", {"ok": True}, ttl_seconds=5)
            checks["sqlite_cache"] = "ok"
        except Exception as exc:
            checks["sqlite_cache"] = f"failed: {type(exc).__name__}"
            overall = "degraded"

        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if deepseek_key and deepseek_key.lower() not in {"placeholder", "dummy", "test", "changeme"}:
            checks["deepseek_key"] = "configured"
        else:
            checks["deepseek_key"] = "missing -- AI synthesis unavailable"
            overall = "degraded"

        status_code = 200 if overall == "ok" else 503
        return JSONResponse({"status": overall, "checks": checks}, status_code=status_code)

    @app.get("/api/health/providers")
    async def provider_health():
        payload = configured_provider_status()
        payload["status"] = "ok"
        return payload

    @app.get("/api/health/llm")
    async def llm_health():
        configured = bool(os.getenv("DEEPSEEK_API_KEY"))
        model_status = deepseek_model_status()
        return {
            "status": "ok" if configured else "degraded",
            "deepseek_configured": configured,
            "default_model": model_status["configured_model"],
            "fast_model": model_status["fast_model"],
            "deep_model": model_status["deep_model"],
            "resolved_fast_model": model_status["resolved_fast_model"],
            "resolved_deep_model": model_status["resolved_deep_model"],
            "thinking_mode": model_status["thinking_mode"],
            "alias_resolution": model_status["alias_resolution"],
            "warnings": [] if configured else ["DEEPSEEK_API_KEY missing; deterministic endpoints continue, synthesis may use fallbacks."],
        }

    return app


app = create_app()

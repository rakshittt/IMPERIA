from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from tradingagents.api.middleware.cache_middleware import CacheMiddleware
from tradingagents.api.middleware.rate_limiter import RateLimitMiddleware
from tradingagents.api.middleware.request_id import RequestIDMiddleware
from tradingagents.api.middleware.security import SecurityHeadersMiddleware
from tradingagents.api.routes import admin, ai, earnings, market, portfolio, research, screener, search, stock, watchlist
from tradingagents.dataflows.provider_registry import configured_provider_status

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(
        title="IMPERIA Finance Intelligence API",
        description="Backend-first US equity intelligence engine with fast answers and deep multi-agent research.",
        version="0.3.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("TRADINGAGENTS_CORS_ORIGINS", "*").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CacheMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

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

    @app.get("/api/health/providers")
    async def provider_health():
        payload = configured_provider_status()
        payload["status"] = "ok"
        return payload

    @app.get("/api/health/llm")
    async def llm_health():
        configured = bool(os.getenv("DEEPSEEK_API_KEY"))
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4")
        return {
            "status": "ok" if configured else "degraded",
            "deepseek_configured": configured,
            "default_model": model,
            "fast_model": os.getenv("DEEPSEEK_FAST_MODEL") or model,
            "deep_model": os.getenv("DEEPSEEK_DEEP_MODEL") or model,
            "warnings": [] if configured else ["DEEPSEEK_API_KEY missing; deterministic endpoints continue, synthesis may use fallbacks."],
        }

    return app


app = create_app()

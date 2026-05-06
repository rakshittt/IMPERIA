from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from tradingagents.api.middleware.cache_middleware import CacheMiddleware
from tradingagents.api.middleware.rate_limiter import RateLimitMiddleware
from tradingagents.api.middleware.security import SecurityHeadersMiddleware
from tradingagents.api.routes import ai, earnings, market, research, screener, search, stock, watchlist

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
    app.include_router(research.router)
    app.include_router(ai.router)

    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        return "<html><body><h1>IMPERIA API</h1><p>US equity intelligence backend is running.</p></body></html>"

    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "product": "IMPERIA",
            "scope": "US equities and major US ETFs, free/open data sources",
        }

    return app


app = create_app()

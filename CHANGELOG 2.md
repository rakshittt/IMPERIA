# IMPERIA Changelog

## 0.3.0

- Rebranded the backend product as **IMPERIA** while preserving the internal `tradingagents` import path.
- Added production hardening: security headers, sliding-window rate limits, validation helpers, DeepSeek helper, and safe HTTP utilities.
- Added specialist deep-research agents: SEC filings, macro context, and earnings/guidance.
- Added DeepSeek context orchestration for fast and deep research contexts.
- Expanded test coverage to 122 passing tests plus 42 subtests.
- Removed old frontend scaffold, generated caches, stale smoke/debug scripts, old assistant metadata, and legacy brand assets.

## 0.2.0

- Added Phase 2 backend layers: market data, news aggregation, earnings data, screener, watchlist persistence, portfolio snapshots, background research jobs, and richer API routes.

## 0.1.0

- Added Phase 1 backend foundation: SEC EDGAR ingestion, computed metrics, SQLite cache, fast query engine, citations, ticker search, and modular API package.

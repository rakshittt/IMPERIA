# IMPERIA Architecture

## System Overview

```text
Client
  -> FastAPI app
     -> security middleware
     -> rate limiter
     -> GET response cache middleware
     -> route module

Stock-first path:
  selected ticker + question
    -> quote, price move, metrics, filings, earnings, news, sector context, Polymarket
    -> citations and warnings
    -> fast answer or queued deep report

Fast path:
  /api/ask or direct stock/market routes
    -> query_router
    -> fast_query
    -> dataflows
    -> SQLite TTL cache
    -> optional DeepSeek synthesis
    -> JSON response with citations and warnings

Deep path:
  POST /api/research
    -> background_jobs.submit_research_job
    -> ThreadPoolExecutor(max_workers=3)
    -> TradingAgentsGraph
    -> analyst reports
    -> specialist reports
    -> bull/bear debate
    -> research manager
    -> trader
    -> risk analyst
    -> portfolio/research synthesizer
    -> persisted result
```

## Fast Path

Fast path is optimized for quick structured answers:

- no full graph run
- cache-first data access
- data-source warnings instead of crashes
- DeepSeek only when a natural-language synthesis is needed
- deterministic fallback when DeepSeek is unavailable

## Deep Research Path

Deep research preserves the TradingAgents graph and adds specialist reports before debate:

```text
Market Analyst
Social Analyst
News Analyst
Fundamentals Analyst
Macro Analyst
SEC Filings Analyst
Macro Context Agent
Earnings Analyst
Bull Researcher
Bear Researcher
Research Manager
Trader Agent
Risk Analyst
Portfolio Manager
```

## Data Sources

| Area | Primary | Fallback |
| --- | --- | --- |
| SEC filings and XBRL | SEC EDGAR | stale SQLite cache |
| Quotes and charts | yfinance | Finnhub, Alpha Vantage, stale cache |
| Market movers/breadth/sectors | yfinance | partial results + warnings |
| News | Finnhub/NewsAPI/NewsData/TheNewsAPI | yfinance, Tavily for deep context |
| Earnings | Finnhub | yfinance |
| Ratios | yfinance statements | SEC XBRL fallback |
| Demo | local deterministic fixtures | no external call required |
| Sentiment | price/news/earnings/sector | read-only Polymarket public endpoints |
| Synthesis | DeepSeek | deterministic template |

## Persistence

Two SQLite stores are used:

- TTL response/data cache: `TRADINGAGENTS_SQLITE_CACHE`
- user/research persistence: `PERSISTENCE_DB_PATH`

Both are local-first and safe for development. For multi-process deployment, move persistence to a managed database later.

## Security And Resilience

- request rate limit per client IP
- separate internal DeepSeek rate limit
- security headers on all responses
- API keys loaded only from environment
- external HTTP calls use timeouts and retries
- provider failure returns warnings or structured errors, not raw stack traces

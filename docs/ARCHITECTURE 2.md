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
    -> quote, price move, metrics, filings, earnings, news, FRED macro,
       sector context, peers, analyst consensus, Form 4, 13F, institutional holders,
       Polymarket
    -> citations and warnings
    -> fast answer or queued deep report

Fast path:
  /api/ask or direct stock/market routes
    -> deterministic planner
    -> adapted financial-services method pack
    -> zero-agent deterministic lookup OR selected expert agents
    -> dataflows + cache
    -> DeepSeek only for synthesis/reasoning when needed
    -> JSON response with citations and warnings

Deep path:
  POST /api/research
    -> background_jobs.submit_research_job
    -> ThreadPoolExecutor(max_workers=3)
    -> stock-first expert-agent graph
    -> research streaming events
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

Deep research is stock-first and does not require portfolio inputs. The legacy TradingAgents graph remains intact for compatibility, but ticker-only `/api/research` requests use the IMPERIA expert-agent graph:

```text
Deterministic Planner
  -> Data Bundle Assembly
     -> SEC EDGAR, yfinance, FRED, Polymarket, news, earnings,
        Form 4, 13F, analyst consensus, peers, institutional holders
  -> Wave 1: News, Price, Fundamentals, Valuation, SEC, Earnings,
             Market Context, Sentiment, Insider/Institutional
  -> Wave 2: Risk, Balanced Thesis, Research Factors
  -> Wave 3: Research Synthesizer
  -> Wave 4: Evidence & Data Quality Auditor
  -> SQLite persistence + SSE stream
```

## Adapted Financial-Services Skill Pack

IMPERIA uses `tradingagents/expert_agents/skill_pack.py` to inject a compact
institutional research-method layer into each expert agent. The methods are
adapted from Anthropic's Apache-2.0 financial-services examples and translated
into IMPERIA's safer stock-research scope.

This layer improves:

- news event materiality
- earnings variance review
- valuation comparability and outlier checks
- sector and competitive landscape framing
- ownership-signal caveats for Form 4, 13F, and institutional holders
- disconfirming-evidence tracking
- source-quality and citation auditing

It is not a separate runtime. Agents still receive assembled data bundles first,
DeepSeek analyzes only that evidence, and final responses remain educational
research rather than action guidance.

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
| Macro | FRED | index/ETF proxies + warnings |
| Ownership | Form 4 and 13F SEC filings | empty structured result + warnings |
| Analyst consensus | Finnhub | unavailable warning |
| Peer comparison | static peer map + free metrics | partial peers + warnings |
| Synthesis | DeepSeek | deterministic template |

## Persistence

SQLite remains the local/demo persistence layer:

- TTL response/data cache: `TRADINGAGENTS_SQLITE_CACHE`
- user/research persistence: `PERSISTENCE_DB_PATH`

Redis is implemented for production-style cache, rate limiting, job-state/event-buffer support, and usage counters where configured with `IMPERIA_CACHE_BACKEND=redis`.

## Security And Resilience

- request rate limit per client IP
- separate internal DeepSeek rate limit
- security headers on all responses
- API keys loaded only from environment
- external HTTP calls use timeouts and retries
- provider failure returns warnings or structured errors, not raw stack traces

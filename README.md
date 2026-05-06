# IMPERIA

**IMPERIA** is an open-source AI research assistant backend for US stocks.

Tagline: **IMPERIA — Source-cited AI research for US stocks.**

It helps a user select a US-listed stock, understand what is happening, inspect the supporting data, and generate source-cited fast answers or deep multi-agent research reports. The product principle is **Data first. AI second.**

The internal Python package is still named `tradingagents` so existing imports and tests keep working. The product, API, docs, and deployment surface are now organized around **IMPERIA**.

> Financial disclaimer: IMPERIA is for educational research only. It does not provide investment advice, personalized financial recommendations, buy/sell/hold instructions, trade execution, or automated portfolio management.

## What IMPERIA Can Do

IMPERIA supports **US-listed equities and major US ETFs only**.

It can:

- Answer stock-specific questions such as “Why is NVDA moving today?”, “What happened to Apple this week?”, “What risks did AMD mention?”, or “What should I watch before Nvidia earnings?”
- Resolve ticker/company searches such as `Apple -> AAPL`.
- Fetch quotes, batch quotes, OHLCV charts, intraday data, index snapshots, sector ETF performance, market movers, and market breadth.
- Fetch and normalize SEC EDGAR data: ticker-to-CIK, recent filings, 10-K/10-Q/8-K/Form 4/13F lists, company facts, and XBRL financials.
- Compute ratios and TTM metrics without paid APIs: P/E, forward P/E when available, EPS, revenue growth, margins, ROE, ROA, debt/equity, current ratio, quick ratio, FCF margin, and EV/EBITDA when inputs exist.
- Aggregate financial news from Finnhub, NewsAPI, NewsData, TheNewsAPI, yfinance, and optional Tavily web search.
- Track earnings calendar, earnings history, next earnings date, beat/miss stats, and surprise percentages.
- Run structured and natural-language stock screeners over a bundled free US equity universe.
- Persist watchlists, portfolio snapshots, and research job results in SQLite.
- Queue deep research jobs in a lightweight background thread pool.
- Run in deterministic demo mode for presentations without external APIs.
- Add optional read-only Polymarket-derived prediction-market sentiment when enabled.
- Run the TradingAgents deep-research graph with market, fundamentals, news, social, SEC filings, macro, earnings, bull/bear debate, risk, trader, and portfolio-manager agents.

## How It Works

```text
Client / API caller
  -> FastAPI app: api.py -> tradingagents.api.main
  -> Routes: stock, market, search, earnings, screener, watchlist, ai, research
  -> Stock-first flow:
       selected ticker + question
       -> quote/news/metrics/filings/earnings/sentiment/citations
       -> fast answer or queued deep research report
  -> Fast mode:
       query_router -> fast_query
       -> market_data/news_aggregator/earnings_data/sec_edgar/computed_metrics
       -> SQLite cache
       -> DeepSeek fast synthesis only when a natural-language answer is needed
       -> structured JSON with citations and warnings
  -> Deep mode:
       POST /api/research
       -> ThreadPoolExecutor(max_workers=3)
       -> TradingAgentsGraph
       -> analyst agents + specialist agents
       -> bull/bear debate + risk + portfolio manager
       -> persisted result in SQLite
```

## Project Structure

```text
api.py                         Compatibility shim for uvicorn api:app
tradingagents/
  api/                         FastAPI app, routes, models, middleware
  agents/                      Deep-research agent roles
  cache/                       SQLite TTL cache and invalidation
  data/                        Bundled US equity universe
  dataflows/                   Market, SEC, news, earnings, screener, metrics
  engine/                      Query router, fast query, citations, DeepSeek context
  graph/                       Existing TradingAgents LangGraph orchestration
  persistence/                 SQLite watchlists, portfolios, research results
  utils/                       Validation, HTTP, DeepSeek helper utilities
  workers/                     Background research job queue
tests/                         Unit and API tests with mocked external providers
scripts/smoke_test.py          Optional live-provider smoke test
docs/                          Product, architecture, API, developer docs
```

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for the developer map.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Create `.env` from `.env.example` and fill only the keys you have:

```bash
cp .env.example .env
```

Run the API:

```bash
uvicorn api:app --reload
```

Open:

```text
http://localhost:8000/api/health
```

## Common API Calls

```bash
curl "http://localhost:8000/api/search?q=Apple"
curl "http://localhost:8000/api/stock/AAPL/profile"
curl "http://localhost:8000/api/stock/AAPL/ratios"
curl "http://localhost:8000/api/stock/AAPL/news"
curl "http://localhost:8000/api/stock/AAPL/what-happened?window=today"
curl "http://localhost:8000/api/stock/AAPL/sentiment"
curl "http://localhost:8000/api/stock/AAPL/research-snapshot"
curl "http://localhost:8000/api/stock/AAPL/investor-checklist"
curl "http://localhost:8000/api/compare?ticker_a=AMD&ticker_b=NVDA"
curl "http://localhost:8000/api/stock/AAPL/next-earnings"
curl "http://localhost:8000/api/market/summary"
curl "http://localhost:8000/api/market/movers"
curl "http://localhost:8000/api/market/breadth"
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","query":"What happened to Apple today?"}'
curl -X POST "http://localhost:8000/api/screener/nl" \
  -H "Content-Type: application/json" \
  -d '{"query":"profitable technology stocks with P/E under 25"}'
```

Queue deep research:

```bash
curl -X POST "http://localhost:8000/api/research" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","question":"Analyze Nvidia as a long-term AI infrastructure company.","window":"past_month","focus":["fundamentals","earnings","filings","news","sentiment"]}'
```

Demo mode for presentations:

```bash
IMPERIA_DEMO_MODE=true uvicorn api:app --reload
```

## Tests

```bash
pytest -q
```

Current expected baseline:

```text
131 passed, 42 subtests passed
```

## Live Smoke Test

This uses real free-provider calls and may be rate-limited:

```bash
python scripts/smoke_test.py
```

## Important Docs

- [Product Brief](docs/PRODUCT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Demo Mode](docs/DEMO_MODE.md)
- [Safety And Limitations](docs/SAFETY_AND_LIMITATIONS.md)
- [Sentiment](docs/SENTIMENT.md)
- [Polymarket Provider](docs/POLYMARKET_PROVIDER.md)
- [Free US Finance Backend Notes](docs/backend_free_us_finance.md)

## Data Sources

Primary/free sources:

- SEC EDGAR submissions and XBRL companyfacts
- yfinance
- Finnhub free-tier when configured
- Alpha Vantage free-tier when configured
- FMP/Twelve Data/EODHD only through already-configured free-tier-safe paths
- NewsAPI, NewsData, TheNewsAPI
- Tavily web search when configured
- Optional read-only Polymarket public endpoints when enabled

IMPERIA does not introduce paid data dependencies.

## Product Status

IMPERIA is backend-first and production-hardened enough for local research workflows, API prototyping, and serious backend iteration. It does not currently ship a frontend; the old frontend scaffold was removed so a new interface can be built cleanly later.

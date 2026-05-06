# IMPERIA

**IMPERIA** is a research-grade US stock intelligence backend. It combines fast market answers with the existing TradingAgents multi-agent deep research engine, using free/open data sources first and DeepSeek for synthesis.

The internal Python package is still named `tradingagents` so existing imports and tests keep working. The product, API, docs, and deployment surface are now organized around **IMPERIA**.

> Financial disclaimer: IMPERIA is for research and education. It does not provide personalized financial advice, trade execution, or automated portfolio management.

## What IMPERIA Can Do

IMPERIA supports **US-listed equities and major US ETFs only**.

It can:

- Answer fast questions such as “What is Apple’s P/E?”, “Why is NVDA moving?”, “Show market movers”, or “When is Tesla’s next earnings?”
- Resolve ticker/company searches such as `Apple -> AAPL`.
- Fetch quotes, batch quotes, OHLCV charts, intraday data, index snapshots, sector ETF performance, market movers, and market breadth.
- Fetch and normalize SEC EDGAR data: ticker-to-CIK, recent filings, 10-K/10-Q/8-K/Form 4/13F lists, company facts, and XBRL financials.
- Compute ratios and TTM metrics without paid APIs: P/E, forward P/E when available, EPS, revenue growth, margins, ROE, ROA, debt/equity, current ratio, quick ratio, FCF margin, and EV/EBITDA when inputs exist.
- Aggregate financial news from Finnhub, NewsAPI, NewsData, TheNewsAPI, yfinance, and optional Tavily web search.
- Track earnings calendar, earnings history, next earnings date, beat/miss stats, and surprise percentages.
- Run structured and natural-language stock screeners over a bundled free US equity universe.
- Persist watchlists, portfolio snapshots, and research job results in SQLite.
- Queue deep research jobs in a lightweight background thread pool.
- Run the TradingAgents deep-research graph with market, fundamentals, news, social, SEC filings, macro, earnings, bull/bear debate, risk, trader, and portfolio-manager agents.

## How It Works

```text
Client / API caller
  -> FastAPI app: api.py -> tradingagents.api.main
  -> Routes: stock, market, search, earnings, screener, watchlist, ai, research
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
curl "http://localhost:8000/api/stock/AAPL/next-earnings"
curl "http://localhost:8000/api/market/summary"
curl "http://localhost:8000/api/market/movers"
curl "http://localhost:8000/api/market/breadth"
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is Apple P/E ratio?"}'
curl -X POST "http://localhost:8000/api/screener/nl" \
  -H "Content-Type: application/json" \
  -d '{"query":"profitable technology stocks with P/E under 25"}'
```

Queue deep research:

```bash
curl -X POST "http://localhost:8000/api/research" \
  -H "Content-Type: application/json" \
  -d '{"portfolio":[{"ticker":"AAPL","weight":0.6},{"ticker":"MSFT","weight":0.4}]}'
```

## Tests

```bash
pytest -q
```

Current expected baseline:

```text
122 passed, 42 subtests passed
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

IMPERIA does not introduce paid data dependencies.

## Product Status

IMPERIA is backend-first and production-hardened enough for local research workflows, API prototyping, and serious backend iteration. It does not currently ship a frontend; the old frontend scaffold was removed so a new interface can be built cleanly later.

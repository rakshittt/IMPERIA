# IMPERIA

**IMPERIA** is an open-source, production-minded AI research backend for US stocks.

Tagline: **IMPERIA — Source-cited AI research for US stocks.**

It helps a user select a US-listed stock, understand what is happening, inspect the supporting data, and generate source-cited fast answers or deep multi-agent research reports. It combines free/open financial data, SEC filings, computed metrics, news, earnings data, read-only prediction-market sentiment, citations, and DeepSeek-v4-powered expert agents. The product principle is **Data first. AI second.**

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
- Add read-only Polymarket-derived prediction-market sentiment as part of stock sentiment when relevant markets exist.
- Use FRED macro data, Form 4 parsing, 13F parsing, analyst consensus, peer comparison, institutional-holder analysis, Redis-backed cache/rate-limit support, research streaming, cost/usage tracking, admin APIs, and portfolio snapshots as production-style backend modules.
- Run a dynamic DeepSeek-v4 expert-agent graph. Fast queries activate only the specialist agents required for the task, while deep research reports run a broader analyst panel. Each agent receives structured evidence, citations, warnings, and data freshness metadata before producing source-grounded JSON output.
- Apply an adapted financial-services skill pack inspired by Anthropic's Apache-2.0 research examples, giving agents stronger event-materiality, earnings-variance, valuation-comparability, competitive-landscape, and evidence-audit discipline while keeping IMPERIA DeepSeek-only and non-advisory.
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
  -> Expert-agent mode:
       deterministic planner
       -> structured evidence bundle
       -> selected specialist agents
       -> research synthesizer
       -> evidence/data-quality auditor
  -> Deep mode:
       POST /api/research
       -> ThreadPoolExecutor(max_workers=3)
       -> stock-first expert-agent panel or legacy graph compatibility
       -> persisted result in SQLite
       -> SSE progress stream
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
  expert_agents/               Stock-first expert-agent graph and planner
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

Built-in frontend app:

```text
http://localhost:8000/app
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
curl "http://localhost:8000/api/health/providers"
curl "http://localhost:8000/api/admin/status"
curl "http://localhost:8000/api/admin/agent-methodology"
curl "http://localhost:8000/api/admin/llm-usage"
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
152 passed, 42 subtests passed
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
- [FRED Macro](docs/FRED_MACRO.md)
- [Form 4 And 13F](docs/FORM4_13F.md)
- [Admin API](docs/ADMIN_API.md)
- [Redis](docs/REDIS.md)
- [Research Streaming](docs/RESEARCH_STREAMING.md)
- [Cost Tracking](docs/COST_TRACKING.md)
- [Anthropic Financial Services Integration](docs/ANTHROPIC_FINANCIAL_SERVICES_INTEGRATION.md)
- [Third-Party Notices](docs/THIRD_PARTY_NOTICES.md)
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
- Read-only Polymarket public endpoints for prediction-market sentiment
- FRED macro indicators when `FRED_API_KEY` is configured
- SEC-derived Form 4 and 13F-related filing data
- Analyst consensus from Finnhub when configured
- Peer and institutional-holder snapshots from free/open sources where available

IMPERIA does not introduce paid data dependencies.

Most deterministic endpoints work without DeepSeek. DeepSeek is used only for synthesis, reasoning, summarization, and expert-style analysis.

IMPERIA implements production-style backend modules for Redis-backed caching/job state, FRED macro data, Polymarket sentiment, Form 4 and 13F parsing, analyst consensus, peer comparison, institutional holder analysis, research streaming, cost tracking, admin APIs, and portfolio snapshots. These modules degrade gracefully when external data is unavailable.

## Product Status

IMPERIA is backend-first and production-hardened enough for local research workflows, API prototyping, and serious backend iteration. The static frontend in `frontend/` is a local dashboard for exploring the backend; it does not add trading, brokerage, payments, or investment-advice functionality.

Limitations: educational/research use only, not investment advice, no trading, no brokerage integration, US equities and major US ETFs only, free data may be delayed/incomplete/rate-limited, and AI output may be wrong and should be verified with citations.

## Frontend

Static SPA. Serve with:

```bash
python -m http.server 3000 --directory frontend
```

Then open:

```text
http://localhost:3000
```

Requires the IMPERIA backend running at:

```text
http://localhost:8000
```

For Codex preview sessions, the same static app can be served on another port, for example:

```bash
python -m http.server 6969 --directory frontend
```

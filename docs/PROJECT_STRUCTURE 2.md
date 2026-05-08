# IMPERIA Project Structure

This repository is backend-first. The old frontend scaffold was removed so the next frontend can be designed cleanly against the API.

## Top Level

```text
api.py                 Compatibility shim for uvicorn api:app
pyproject.toml         Python package metadata
requirements.txt       Runtime dependencies
requirements-dev.txt   Runtime + test dependencies
Dockerfile             Container build
docker-compose.yml     Local container runner
README.md              Main product entry point
CHANGELOG.md           Product change history
docs/                  Product and developer docs
scripts/               Manual smoke scripts
tests/                 Unit/API tests
tradingagents/         Backend package
```

## Backend Package

```text
tradingagents/api/
  main.py              FastAPI app factory
  models.py            Public request/response contracts
  routes/              Route modules by product area
  middleware/          Security, cache, rate-limit middleware
  services.py          API service helpers and research normalization

tradingagents/dataflows/
  market_data.py       Quotes, batch quotes, OHLCV, movers, breadth, sectors
  sec_edgar.py         SEC ticker/CIK, filings, companyfacts, XBRL, Form 4, 13F
  fred_macro.py        FRED macro indicators with ETF-proxy degradation
  form4_parser.py      Structured Form 4 insider activity wrapper
  thirteen_f_parser.py Structured 13F-related filing wrapper
  analyst_consensus.py Finnhub analyst consensus wrapper
  peer_comparison.py   Peer basket and free metric comparison
  institutional_holders.py
                       Institutional holder and 13F context
  news_aggregator.py   Finnhub/NewsAPI/NewsData/TheNewsAPI/yfinance merge
  earnings_data.py     Calendar, history, next earnings, surprise stats
  screener.py          Structured and natural-language stock screener
  computed_metrics.py  TTM and ratio calculations

tradingagents/engine/
  fast_query.py        Tier 1 fast answer engine
  query_router.py      Fast vs deep routing
  citation_tracker.py  Structured source tracking
  deepseek_orchestrator.py
                       Context gathering for DeepSeek synthesis
  search/              Ticker resolver, query parser, answer synthesizer

tradingagents/expert_agents/
  planner.py           Deterministic intent routing and agent selection
  runtime.py           Evidence assembly and expert-agent orchestration
  cache.py             Agent output cache using input-data hashes
  prompts.py           Universal DeepSeek rules and prompt text
  agents/              News, price, fundamentals, valuation, SEC, earnings,
                       market context, sentiment, risk, balanced thesis,
                       insider/institutional, research factors, synthesis,
                       evidence/data-quality audit

tradingagents/agents/
  analysts/            Market, fundamentals, news, macro, SEC, earnings agents
  researchers/         Bull and bear debate agents
  managers/            Research and portfolio manager agents
  risk_mgmt/           Risk analyst
  trader/              Trader assessment agent
  utils/               Agent state, tools, memory, structured-output helpers

tradingagents/graph/
  trading_graph.py     Core LangGraph orchestration
  setup.py             Node/edge setup
  propagation.py       Initial graph state
  conditional_logic.py Debate/tool-loop control

tradingagents/cache/
  sqlite_cache.py      TTL cache
  redis_cache.py       Redis production-style cache/status helper
  keys.py              Stable input-data-hash cache keys
  invalidation.py      Cache invalidation helpers

tradingagents/persistence/
  db.py                SQLite persistence wrapper
  watchlist.py         Watchlist CRUD
  portfolio.py         Portfolio snapshots and research result persistence
  usage.py             LLM usage, agent runs, and admin error records

tradingagents/workers/
  background_jobs.py   ThreadPoolExecutor research queue

tradingagents/utils/
  validation.py        Ticker/date validation
  http.py              Safe retries/timeouts
  deepseek.py          DeepSeek-only call helper and internal limiter
```

## What Not To Put Back

Avoid committing:

- frontend build output
- `node_modules`
- `.next`
- `.pytest_cache`
- `.tradingagents_data`
- assistant/editor worktree metadata
- one-off root scripts such as `test_nvda.py`
- local secrets or `.env`

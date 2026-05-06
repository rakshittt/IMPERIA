# IMPERIA Free US Finance Backend Notes

## Architecture

IMPERIA exposes a two-tier backend for US-listed equities and major US ETFs only.

- Tier 1 fast query uses yfinance, SEC EDGAR, computed ratios, search resolution, SQLite caching, news/earnings aggregation, and structured citations.
- Tier 2 deep research preserves the existing `TradingAgentsGraph.analyze_portfolio` multi-agent workflow.
- The root `api.py` remains a compatibility shim for `uvicorn api:app`; the real app lives in `tradingagents/api/main.py`.

```text
HTTP API
  -> route modules
  -> fast dataflows: market_data, news_aggregator, earnings_data, screener
  -> cache/persistence: SQLite TTL cache + user_data.db
  -> optional synthesis: DeepSeek fast response synthesizer
  -> deep research: ThreadPoolExecutor jobs around TradingAgentsGraph
       -> market/fundamentals/news/social/macro analysts
       -> SEC filings + macro context + earnings specialist agents
       -> bull/bear debate -> research manager -> trader -> risk -> portfolio manager
```

## Data Source Matrix

| Capability | Primary | Fallbacks |
| --- | --- | --- |
| Quotes | yfinance | Finnhub, Alpha Vantage, stale SQLite cache |
| Batch quotes, movers, breadth, sectors | yfinance | stale SQLite cache |
| SEC filings/XBRL/Form 4/13F | SEC EDGAR | stale SQLite cache |
| Stock news | Finnhub | NewsAPI, NewsData, TheNewsAPI, yfinance |
| Market news | NewsAPI | NewsData, TheNewsAPI |
| Earnings calendar/history | Finnhub | yfinance |
| Fast synthesis | DeepSeek | deterministic template |
| Deep research synthesis | DeepSeek | specialist deterministic placeholders on source failure |
| Deep context orchestration | DeepSeekContextOrchestrator | per-source timeout warnings |
| Screener metrics | computed_metrics/yfinance | cached values, SEC fallback inside computed metrics |

Paid-only feeds such as Bloomberg, FactSet, S&P Global paid feeds, Morningstar paid feeds, Quiver paid APIs, Quartr paid APIs, and premium-only EODHD features are not used by the backend.

## Environment

Set `SEC_USER_AGENT` in production so SEC requests identify your app/operator.

```bash
SEC_USER_AGENT="IMPERIA/0.3.0 contact=you@example.com"
TRADINGAGENTS_SQLITE_CACHE="$HOME/.tradingagents/cache/backend_cache.sqlite3"
TRADINGAGENTS_API_RATE_LIMIT=120
TRADINGAGENTS_API_CACHE_TTL=15
PERSISTENCE_DB_PATH="./.tradingagents_data/user_data.db"
DEEPSEEK_API_KEY=
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
FINANCIAL_MODELING_PREP_API_KEY=
TWELVE_DATA_API_KEY=
EODHD_API_KEY=
NEWSAPI_API_KEY=
NEWSDATA_API_KEY=
THENEWSAPI_COM_API_TOKEN=
THENEWSAPI_API_TOKEN=
TAVILY_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_FAST_MODEL=deepseek-v4-flash
DEEPSEEK_DEEP_MODEL=deepseek-v4-pro
DEEPSEEK_CALLS_PER_MINUTE=20
```

Do not hardcode API keys in source files or docs. The API loads keys from the process environment or `.env`.
Some keys are retained for compatibility with existing project integrations. Core fast-market intelligence uses only free-tier-safe paths and does not call paid-only EODHD, Quiver, Quartr, Bloomberg, FactSet, S&P Global, or Morningstar feeds.

## Phase 3 Hardening

- All API responses include `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.
- API rate limiting uses a per-client sliding window from `TRADINGAGENTS_API_RATE_LIMIT`; DeepSeek has a separate 20 calls/minute internal limiter.
- Ticker inputs are normalized to US-style symbols and invalid symbols return 422 instead of 500.
- Date inputs are validated as ISO `YYYY-MM-DD`.
- Deep research now has additive specialist context before bull/bear debate: SEC filings, macro/sector context, and earnings/guidance.
- `DeepSeekContextOrchestrator` gathers fast and deep context bundles concurrently with per-source timeouts and warning capture.

## Endpoint Reference

| Endpoint | Purpose |
| --- | --- |
| `GET /api/search?q=apple` | Ticker/company search |
| `POST /api/ask` | Fast/deep query routing |
| `GET /api/stock/{ticker}/profile` | Company profile |
| `GET /api/stock/{ticker}/financials` | SEC/computed financials |
| `GET /api/stock/{ticker}/ratios` | Computed ratios |
| `GET /api/stock/{ticker}/chart` | OHLCV records |
| `GET /api/stock/{ticker}/intraday` | Intraday OHLCV records |
| `GET /api/stock/{ticker}/news` | Aggregated stock news |
| `GET /api/stock/{ticker}/earnings` | Earnings surprise history |
| `GET /api/stock/{ticker}/next-earnings` | Next earnings event |
| `GET /api/stock/{ticker}/holders` | Holder data and SEC 13F limitation note |
| `GET /api/market/indices` | SPY, QQQ, DIA, IWM, VIX snapshot |
| `GET /api/market/movers` | Top gainers/losers from bundled US universe |
| `GET /api/market/breadth` | Advancing/declining/unchanged breadth |
| `GET /api/market/sectors` | Sector ETF performance |
| `GET /api/market/summary` | Indices, movers, breadth, market news |
| `GET /api/earnings/calendar` | Earnings calendar |
| `GET /api/earnings/{ticker}/history` | Earnings history |
| `GET /api/earnings/{ticker}/next` | Next earnings event |
| `POST /api/screener/run` | Structured screener criteria |
| `POST /api/screener/nl` | Natural-language screener |
| `POST /api/watchlist` | Create watchlist |
| `GET /api/watchlist` | List watchlists |
| `GET /api/watchlist/{id}/quotes` | Watchlist quotes |
| `POST /api/research` | Queue deep research job |
| `GET /api/research` | List persisted research jobs |
| `GET /api/research/{id}` | Research job status/result |
| `GET /api/research/stream/{id}` | SSE status stream |

Compatibility routes remain: `POST /api/analyze`, `GET /api/quote/{ticker}`, `GET /api/trending`, and `GET /api/market-snapshot`.

## Free-Tier Rate Notes

- SEC EDGAR: identify with `SEC_USER_AGENT` and keep request rate modest.
- yfinance: unofficial, can rate-limit or change schemas.
- Finnhub, Alpha Vantage, NewsAPI, NewsData, and TheNewsAPI: free tiers have request limits; provider calls use timeouts, retries, and cache/stale fallback where practical.
- DeepSeek synthesis is optional for fast answers and falls back to deterministic cited text if unavailable. Deep research is configured to use DeepSeek provider/model names by default.

## Limitations

- SEC facts are official but not uniform across issuers; missing concepts return absent metrics rather than fabricated values.
- Form 4 support parses transactions when XML documents are directly accessible; otherwise filings are still returned.
- 13F support exposes issuer-related filings for the resolved CIK and documents the limitation. Full issuer-level institutional ownership aggregation requires parsing manager information tables across the full 13F universe.
- Non-US equities, crypto, forex, OTC symbols, and detectable ADR/ADS listings are unsupported.
- The bundled screener/movers universe is a practical free-source approximation, not a guaranteed full Russell 1000 feed.
- Background research jobs are process-local; completed results/status are persisted, but queued in-memory futures do not survive process restarts.

## Smoke Test

Run the live smoke test manually:

```bash
.venv/bin/python scripts/smoke_test.py
```

It checks AAPL/MSFT quotes, market indices, movers, SEC CIK lookup, a fast query, and a simple screener query using real free-provider calls.

## Migration Notes

Existing `uvicorn api:app --reload` and `/api/analyze` clients continue to work. New clients should prefer the modular `/api/stock/*`, `/api/market/*`, `/api/ask`, and `/api/research` routes.

# Free US Finance Backend Notes

## Architecture

TradingAgents now exposes a two-tier backend for US-listed equities and major US ETFs only.

- Tier 1 fast query uses yfinance, SEC EDGAR, computed ratios, search resolution, SQLite caching, and structured citations.
- Tier 2 deep research preserves the existing `TradingAgentsGraph.analyze_portfolio` multi-agent workflow.
- The root `api.py` remains a compatibility shim for `uvicorn api:app`; the real app lives in `tradingagents/api/main.py`.

## Data Sources

- SEC EDGAR submissions and XBRL companyfacts are used for official filings and normalized financial facts.
- yfinance is used for free quote, profile, chart, news, holder, and earnings data.
- Alpha Vantage and Finnhub remain optional free-tier providers where already configured in the repo.
- FMP can be used as an optional existing-key profile fallback when available; it is not required and is not treated as a paid dependency.
- Paid-only feeds such as Bloomberg, FactSet, S&P Global paid feeds, Morningstar paid feeds, Quiver paid APIs, Quartr paid APIs, and premium-only EODHD features are not used by the new backend.

## Environment

Set `SEC_USER_AGENT` in production so SEC requests identify your app/operator.

```bash
SEC_USER_AGENT="TradingAgents/0.2.4 contact=you@example.com"
TRADINGAGENTS_SQLITE_CACHE="$HOME/.tradingagents/cache/backend_cache.sqlite3"
TRADINGAGENTS_API_RATE_LIMIT=120
TRADINGAGENTS_API_CACHE_TTL=15
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
FINANCIAL_MODELING_PREP_API_KEY=
```

Do not hardcode API keys in source files or docs. The API loads keys from the process environment or `.env`.

## Routes

Fast endpoints:

- `GET /api/search?q=apple`
- `GET /api/stock/{ticker}/profile`
- `GET /api/stock/{ticker}/financials`
- `GET /api/stock/{ticker}/ratios`
- `GET /api/stock/{ticker}/chart`
- `GET /api/stock/{ticker}/news`
- `GET /api/stock/{ticker}/earnings`
- `GET /api/stock/{ticker}/holders`
- `GET /api/stock/{ticker}/ai-summary`
- `GET /api/market/indices`
- `GET /api/market/movers`
- `GET /api/market/summary`
- `POST /api/ask`

Deep research and compatibility endpoints:

- `POST /api/research`
- `GET /api/research/{id}`
- `POST /api/research/stream`
- `POST /api/analyze`
- `GET /api/quote/{ticker}`
- `GET /api/trending`
- `GET /api/market-snapshot`

## Limitations

- SEC facts are official but not uniform across issuers; missing concepts return absent metrics rather than fabricated values.
- yfinance is free and useful but unofficial; requests can rate-limit or return schema changes.
- Form 4 support parses transactions when XML documents are directly accessible; otherwise filings are still returned.
- 13F support exposes issuer-related filings for the resolved CIK and documents the limitation. Full issuer-level institutional ownership aggregation requires parsing manager information tables across the full 13F universe.
- Non-US equities, crypto, forex, OTC symbols, and detectable foreign ADR/ADS listings are unsupported.

## Migration Notes

Existing `uvicorn api:app --reload` and `/api/analyze` clients continue to work. New clients should prefer the modular `/api/stock/*`, `/api/market/*`, `/api/ask`, and `/api/research` routes.

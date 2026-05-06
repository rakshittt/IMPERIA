# IMPERIA API Reference

Run locally:

```bash
uvicorn api:app --reload
```

Base URL:

```text
http://localhost:8000
```

## Health

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Service health and product scope |

## Search And AI

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/search?q=Apple` | Ticker/company search |
| POST | `/api/ask` | Fast/deep natural-language query routing |
| POST | `/api/analyze` | Compatibility synchronous deep-analysis route |

Example:

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is Apple P/E ratio?"}'
```

## Stock

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/stock/{ticker}/profile` | Company profile |
| GET | `/api/stock/{ticker}/financials` | Computed + SEC XBRL financials |
| GET | `/api/stock/{ticker}/ratios` | Computed ratio payload |
| GET | `/api/stock/{ticker}/chart` | OHLCV chart records |
| GET | `/api/stock/{ticker}/intraday` | Intraday OHLCV records |
| GET | `/api/stock/{ticker}/news` | Aggregated stock news |
| GET | `/api/stock/{ticker}/earnings` | Earnings surprise history |
| GET | `/api/stock/{ticker}/next-earnings` | Next earnings event |
| GET | `/api/stock/{ticker}/holders` | Holder data and SEC limitation note |
| GET | `/api/stock/{ticker}/filings` | SEC filing list |
| GET | `/api/stock/{ticker}/insiders` | Form 4 insider activity |
| GET | `/api/stock/{ticker}/ai-summary` | Fast AI stock summary |

## Market

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/market/indices` | SPY, QQQ, DIA, IWM, VIX |
| GET | `/api/market/movers` | Gainers and losers |
| GET | `/api/market/breadth` | Advancing/declining/unchanged counts |
| GET | `/api/market/sectors` | Sector ETF performance |
| GET | `/api/market/summary` | Combined market snapshot |

## Earnings

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/earnings/calendar` | Earnings events |
| GET | `/api/earnings/{ticker}/history` | Earnings history |
| GET | `/api/earnings/{ticker}/next` | Next earnings event |
| GET | `/api/earnings/{ticker}/surprise-stats` | Beat/miss statistics |

## Screener

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/screener/run` | Run structured criteria |
| POST | `/api/screener/nl` | Parse natural language criteria and run |

Example:

```bash
curl -X POST "http://localhost:8000/api/screener/nl" \
  -H "Content-Type: application/json" \
  -d '{"query":"profitable technology stocks with P/E under 25"}'
```

## Watchlist

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/watchlist` | Create watchlist |
| GET | `/api/watchlist` | List watchlists |
| GET | `/api/watchlist/{id}` | Read one watchlist |
| POST | `/api/watchlist/{id}/tickers` | Add ticker |
| DELETE | `/api/watchlist/{id}/tickers/{ticker}` | Remove ticker |
| DELETE | `/api/watchlist/{id}` | Delete watchlist |
| GET | `/api/watchlist/{id}/quotes` | Hydrate watchlist quotes |

## Research

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/research` | Queue deep research |
| GET | `/api/research` | List persisted research jobs |
| GET | `/api/research/{id}` | Status/result |
| GET | `/api/research/stream/{id}` | SSE status stream |
| POST | `/api/research/stream` | Compatibility stream submit route |

## Validation Rules

- ticker max length: 6
- ticker characters: `A-Z`, `0-9`, `.`, `-`
- unsupported: crypto, forex, international equities, OTC
- dates: ISO `YYYY-MM-DD`
- screener numeric bounds must be non-negative and min <= max

# IMPERIA Data Sources

IMPERIA uses free/open sources first and free-tier provider keys only when configured. The modules below are required backend capabilities, but each provider can still return no data, be unconfigured, or fail. IMPERIA returns structured warnings instead of fabricating data.

## Provider Order

```text
SQLite cache
  -> demo fixtures when IMPERIA_DEMO_MODE=true
  -> SEC EDGAR / yfinance / local computed metrics
  -> configured optional free-tier providers
  -> stale cache fallback with warning
```

## Sources

| Area | Primary | Optional fallback |
| --- | --- | --- |
| Quotes/charts | yfinance, demo fixtures | Finnhub, Alpha Vantage |
| SEC filings/XBRL | SEC EDGAR | demo fixtures |
| Metrics | yfinance statements, SEC fallback | demo fixtures |
| News | Finnhub, NewsAPI, NewsData, TheNewsAPI, yfinance | demo fixtures |
| Earnings | Finnhub, yfinance | demo fixtures |
| Sentiment | price/news/earnings/sector signals, Polymarket public endpoints | uncertain result + warning when no relevant market exists |
| Macro | FRED | ETF/index proxies + warning |
| Insider activity | SEC Form 4 parser | empty activity + warning |
| Institutional activity | SEC 13F-related filings, yfinance holders | empty holder result + lag warning |
| Analyst consensus | Finnhub | unavailable warning |
| Peer comparison | static peer map + free quote/metrics data | partial peer result + warnings |
| Cost/usage | SQLite usage tables, Redis when configured | local usage-only summary |

Missing providers should produce warnings, not fabricated data.

## Required Modules With Graceful Degradation

- Polymarket sentiment: read-only public endpoints; no trading/wallet logic.
- FRED macro data: uses `FRED_API_KEY`; if missing, market context falls back to ETF/index proxies.
- Form 4 parser: SEC-derived insider activity; empty results are normal for many tickers.
- 13F parser: SEC-derived and lagged by nature; issuer-level ownership is incomplete in free data.
- Analyst consensus: Finnhub when configured; never treated as IMPERIA advice.
- Peer comparison: static peer map and free metrics.
- Institutional holders: yfinance holder table and 13F context where available.
- Redis: production-style cache, rate-limit, and event-buffer support when configured.

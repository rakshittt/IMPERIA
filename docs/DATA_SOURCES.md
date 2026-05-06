# IMPERIA Data Sources

IMPERIA uses free/open sources first and optional free-tier providers only when keys are configured.

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

Missing providers should produce warnings, not fabricated data.

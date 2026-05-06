# IMPERIA Product Brief

## What IMPERIA Is

IMPERIA is a backend intelligence system for US stocks and major US ETFs. It is built to feel closer to a financial answer engine than a simple market-data wrapper:

- fast enough for common quote/news/ratio/market questions
- deep enough for multi-agent portfolio research
- structured enough for a future frontend, mobile app, or internal dashboard
- free-source-first, with clear warnings when data is missing or rate-limited

## Users

Primary users:

- individual researchers who want fast US equity intelligence
- developers building a Perplexity Finance-style product
- analysts who want a repeatable backend for portfolio research

## Product Modes

### Fast Query Mode

Fast mode avoids the full agent graph. It fetches live/cached structured data, optionally asks DeepSeek to synthesize a cited paragraph, and returns JSON.

Best for:

- current quote
- P/E and computed ratios
- company profile
- recent news
- earnings history and next earnings
- market summary
- movers and breadth
- quick “why is this stock moving?” questions

### Deep Research Mode

Deep mode queues a background job and runs the TradingAgents graph. It uses analyst reports, specialist reports, bull/bear debate, risk synthesis, trader assessment, and portfolio manager feedback.

Best for:

- portfolio review
- long-term thesis work
- bull vs bear research
- risk analysis
- investment committee-style summaries

## Data Philosophy

IMPERIA uses free/open data sources first:

- SEC EDGAR for official filings and XBRL facts
- yfinance for quotes/charts/holders where available
- free-tier Finnhub and Alpha Vantage fallbacks
- free-tier news providers when configured
- DeepSeek only for synthesis, routing, and NLP parsing

No paid market-data dependency is introduced by the backend.

## Current Limitations

- US equities and major US ETFs only
- yfinance is unofficial and can change schemas
- SEC XBRL concepts vary by issuer
- Form 4 parsing depends on accessible XML documents
- Full 13F ownership aggregation is not equivalent to paid ownership feeds
- background jobs are process-local, though status and results persist to SQLite
- no frontend is shipped right now

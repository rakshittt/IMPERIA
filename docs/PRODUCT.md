# IMPERIA Product Brief

## What IMPERIA Is

IMPERIA is an open-source AI research assistant backend for US stocks and major US ETFs. It is built around a stock-first flow: select a ticker, ask what is happening, gather real data and citations, then synthesize an educational research answer.

- fast enough for common quote/news/ratio/market questions
- deep enough for multi-agent single-stock research reports
- structured enough for a future frontend, mobile app, or internal dashboard
- free-source-first, with clear warnings when data is missing or rate-limited

## Users

Primary users:

- individual researchers who want fast US equity intelligence
- developers building a Perplexity Finance-style product
- students, professors, recruiters, and reviewers evaluating a serious capstone backend

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
- stock sentiment, what-happened, risks, bull/bear, filing brief, earnings brief, and research checklist endpoints

### Deep Research Mode

Deep mode queues a background job and runs the TradingAgents graph. It now accepts a ticker-first request without portfolio details and internally adapts that ticker into the existing graph.

Best for:

- long-term thesis work
- bull vs bear research
- risk analysis
- expert-style source-cited stock reports

## Data Philosophy

IMPERIA uses free/open data sources first:

- SEC EDGAR for official filings and XBRL facts
- yfinance for quotes/charts/holders where available
- free-tier Finnhub and Alpha Vantage fallbacks
- free-tier news providers when configured
- DeepSeek only for synthesis, routing, and NLP parsing
- optional read-only Polymarket public data for prediction-market sentiment when enabled

No paid market-data dependency is introduced by the backend.

## Current Limitations

- US equities and major US ETFs only
- yfinance is unofficial and can change schemas
- SEC XBRL concepts vary by issuer
- Form 4 parsing depends on accessible XML documents
- Full 13F ownership aggregation is not equivalent to paid ownership feeds
- background jobs are process-local, though status and results persist to SQLite
- no frontend is shipped right now
- no personalized buy/sell/hold or allocation advice is provided

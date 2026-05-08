# Form 4 And 13F Modules

Form 4 parsing and 13F-related analysis are required IMPERIA backend modules.

## Form 4

The Form 4 parser wraps SEC EDGAR filing metadata and parses non-derivative transactions when XML is available.

Output includes:

- filing date
- transaction code
- shares
- price
- acquired/disposed flag
- filing citation
- warnings

Always remember: insider selling may be pre-planned under 10b5-1 plans. A single sale is not automatically bearish.

## 13F

The 13F parser exposes issuer-related 13F-HR records where available and documents the limitation of free SEC data. 13F data is lagged by nature and should not be treated as live institutional positioning.

Institutional-holder analysis combines 13F context with yfinance holder tables when available.

If no data exists, IMPERIA returns an empty structured result with warnings instead of crashing.

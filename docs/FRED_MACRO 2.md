# FRED Macro Module

FRED macro data is a required IMPERIA backend module for Market Context analysis.

Environment:

```bash
FRED_API_KEY=
```

When configured, IMPERIA fetches macro series such as fed funds, CPI, unemployment, 10-year yield, and a dollar-index proxy from FRED. When unconfigured or unavailable, the module returns a structured warning and the Market Context Analyst continues using broad-index, VIX, sector ETF, and peer proxies.

Important behavior:

- no API key is logged or returned
- failures return warnings, not 500s
- FRED data is not used for deterministic raw stock lookups
- stale/missing macro data lowers confidence

Health visibility:

```text
GET /api/health/providers
GET /api/admin/providers
```

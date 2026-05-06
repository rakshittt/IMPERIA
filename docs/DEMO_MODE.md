# IMPERIA Demo Mode

Set:

```bash
IMPERIA_DEMO_MODE=true
```

Demo mode uses deterministic local fixtures for presentation-safe stock research flows. It does not require external market/news/SEC provider access for common demo queries.

Fixtures live in:

```text
tradingagents/data/demo/
```

Covered fixture types:

- quotes
- profiles
- computed metrics
- news
- earnings
- SEC filing examples
- sentiment
- deep research demo reports
- demo universe

All demo responses include warnings that the data is sample educational data, not live market data.


# IMPERIA Sentiment

The sentiment endpoint is research sentiment, not investment advice.

```text
GET /api/stock/{ticker}/sentiment?window=today
```

Labels:

- bullish
- neutral
- bearish
- mixed
- uncertain

Signals:

- price action
- relative volume when available
- news sentiment
- earnings history
- sector movement
- market movement
- Polymarket-derived prediction-market signals when relevant public markets exist
- analyst consensus when Finnhub is configured
- institutional-holder and 13F context when available

The endpoint never returns buy/sell/hold recommendations.

Polymarket is a required read-only backend module, but many stocks have no relevant prediction market. In that case the sentiment payload includes an `uncertain` Polymarket sub-signal and a warning rather than treating it as an error.

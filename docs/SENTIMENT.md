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

The endpoint never returns buy/sell/hold recommendations.

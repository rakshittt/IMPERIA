# IMPERIA Polymarket Provider

Polymarket support is optional, disabled by default, and read-only.

Set:

```bash
IMPERIA_ENABLE_POLYMARKET=true
```

Used endpoints are public read endpoints:

- `https://gamma-api.polymarket.com`
- `https://data-api.polymarket.com`
- `https://clob.polymarket.com`

IMPERIA does not implement wallets, private keys, order placement, order cancellation, deposits, withdrawals, or trading.

Output is labeled as prediction-market sentiment or event-market signal, not a stock rating, analyst consensus, or investment recommendation.

If no relevant market is found, the provider returns:

```json
{
  "sentiment_label": "uncertain",
  "confidence_score": 0,
  "warnings": ["No sufficiently relevant Polymarket markets found for this ticker."]
}
```


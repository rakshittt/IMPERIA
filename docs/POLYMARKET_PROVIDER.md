# IMPERIA Polymarket Provider

Polymarket support is built into IMPERIA sentiment as a required read-only public-data provider.

Used endpoints are public read endpoints:

- `https://gamma-api.polymarket.com`
- `https://data-api.polymarket.com`
- `https://clob.polymarket.com`

IMPERIA does not implement wallets, private keys, order placement, order cancellation, deposits, withdrawals, or trading. No Polymarket API key is required.

Output is labeled as prediction-market sentiment or event-market signal, not a stock rating, analyst consensus, or investment recommendation.

The Market Sentiment Agent always attempts to include Polymarket-derived context when it runs. Most tickers will have no sufficiently relevant active event market; that is a normal structured result, not a backend failure.

If no relevant market is found, the provider returns:

```json
{
  "sentiment_label": "uncertain",
  "confidence_score": 0,
  "warnings": ["No sufficiently relevant Polymarket markets found for this ticker."]
}
```

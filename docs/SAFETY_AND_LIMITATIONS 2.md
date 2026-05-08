# IMPERIA Safety And Limitations

IMPERIA is for educational stock research. It does not provide personalized investment advice, portfolio allocation, buy/sell/hold instructions, trade execution, guarantees, or brokerage functionality.

Allowed wording:

- Here are factors to consider.
- The data suggests.
- Research sentiment appears bullish, bearish, neutral, mixed, or uncertain.
- Key risks to watch are.

Avoided wording:

- You should buy.
- You should sell.
- This is a hold.
- Guaranteed.
- Risk-free.
- Put a specific percentage of your money into this stock.

When a user asks for direct advice, the backend reframes the response into research factors and includes: `Educational research only. Not investment advice.`

Every final expert-agent response exposes the broader disclaimer:

```text
IMPERIA is an educational research tool. It is not financial advice, not an investment recommendation, and not a trading instruction. Data may be stale or incomplete.
```

The Research Factors Agent produces questions and factors to research. It does not produce pass/fail verdicts, allocation guidance, or trading instructions.

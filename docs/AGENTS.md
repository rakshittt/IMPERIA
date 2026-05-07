# IMPERIA Expert-Agent Graph

IMPERIA uses software analysis modules. They are not humans and they do not fetch data directly.

Core rule: **data first, DeepSeek second**. Dataflows assemble a structured evidence bundle with citations, warnings, provider metadata, and freshness. Agents analyze only that bundle and return structured JSON.

## Components

| Component | Responsibility |
| --- | --- |
| Deterministic Query Router / Planner | Classifies intent, window, mode, and selected agent set without DeepSeek when rules are enough |
| News & Event Analyst | Recent company news, events, catalysts, themes, article sentiment |
| Price Action Analyst | Price/volume movement, relative volume, 52-week context, unusual move flag |
| Fundamentals Analyst | Growth, margins, returns, balance sheet, liquidity, cash flow |
| Valuation Analyst | P/E, forward P/E, EV/EBITDA, market cap, valuation risk |
| SEC Filings & Regulatory Analyst | SEC filing metadata, risk-factor context, Form 4 and 13F notes |
| Earnings Analyst | Next earnings, EPS estimates, surprise history, beat/miss pattern |
| Market Context Analyst | FRED macro, broad indices, VIX, sector ETFs, peers, competitive context |
| Market Sentiment Agent | News/price/earnings/sector/analyst/institutional/Polymarket sentiment |
| Risk Analyst | Business, financial, valuation, regulatory, macro, execution risks |
| Balanced Thesis Agent | Bullish and bearish research cases in one balanced output |
| Insider & Institutional Activity Agent | Form 4 transactions, 13F-related data, institutional holder context |
| Research Factors Agent | Educational factors to research and verify, no pass/fail verdicts |
| Research Synthesizer | Final user-facing source-cited research narrative |
| Evidence & Data Quality Auditor | Citation validation, advice-language scan, provider failures, data quality |

## Universal Output Contract

Every agent output includes:

```json
{
  "agent_name": "",
  "ticker": "",
  "company_name": "",
  "task": "",
  "summary": "",
  "key_findings": [],
  "positive_signals": [],
  "negative_signals": [],
  "uncertainties": [],
  "confidence_score": 0,
  "citations": [],
  "warnings": [],
  "not_investment_advice": true,
  "generated_at": "",
  "data_freshness": {
    "oldest_input_ts": null,
    "newest_input_ts": null,
    "stale_data_flag": false
  }
}
```

## Fast vs Deep

Fast mode activates only the needed agents, usually 3-7. Raw lookups such as quote, market cap, P/E, filing lists, and earnings dates use zero DeepSeek agents.

Deep mode runs the broader panel and is queued through the background research job system. It returns a `research_id` immediately, then clients can poll or stream status.

## Safety

Agents must not say buy, sell, hold, strong buy, strong sell, guaranteed, risk-free, or personalized allocation language. Allowed labels are bullish, bearish, neutral, mixed, and uncertain. The output is educational research, not advice.

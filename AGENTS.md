# IMPERIA Agent Architecture

IMPERIA runs two research paths:

## 1. Stock-First Expert Agent Graph (primary)

**Entry point:** `tradingagents/expert_agents/runtime.py` -- `ExpertAgentRuntime`

Used for single-ticker queries via `POST /api/research` (with `ticker`) and all fast AI endpoints.

**Flow:**
1. `plan_query()` -- determine intent and time window
2. `assemble_evidence_bundle()` -- gather quote, news, metrics, SEC filings, earnings, macro, peers, sentiment, Polymarket, analyst consensus, Form 4, 13F, institutional holders
3. `selected_agents_for_intent()` -- pick the agent subset for this query type
4. Run each agent in sequence via `run_agent()`, passing upstream outputs
5. DeepSeek refinement (if key configured) via `_refine_with_deepseek()`
6. Return `ExpertGraphResult`

**Agents:** `fundamentals`, `news`, `sentiment`, `risk`, `earnings`, `sec_filings`, `macro`, `peer_comparison`, `insider_activity`, `synthesizer`, `evidence_auditor`

**File:** `tradingagents/expert_agents/agents/registry.py`

## 2. Portfolio LangGraph Research (legacy)

**Entry point:** `tradingagents/graph/trading_graph.py` -- `TradingAgentsGraph`

Used for multi-ticker portfolio research via `POST /api/research` (with `portfolio`) and the CLI `analyze` command.

**Nodes:** market analyst, social analyst, news analyst, fundamentals analyst, macro analyst, SEC filings specialist, earnings specialist, bull researcher, bear researcher, trader, risk manager, portfolio manager

## Data Sources

All evidence is collected from free/open providers with graceful fallback:

| Source | Provider | TTL |
|--------|----------|-----|
| Quotes / OHLCV | yfinance | 60s |
| News | Finnhub, NewsAPI, NewsData, TheNewsAPI, yfinance | 5m |
| SEC filings | SEC EDGAR (free) | 1h |
| Earnings | yfinance | 6h |
| Macro indicators | FRED (optional key) | 1h |
| Prediction market sentiment | Polymarket (read-only public API) | 5m |
| Analyst consensus | Finnhub free tier | 30m |
| Peer comparison | yfinance | 24h |
| Form 4 / 13F | SEC EDGAR | 24h |
| Institutional holders | yfinance | 24h |

## Skill Pack

`tradingagents/expert_agents/skill_pack.py` -- adapted financial-services discipline prompts applied per agent. Covers event materiality, earnings-variance, valuation-comparability, competitive-landscape, and evidence-audit.

## Safety

All agent outputs are checked by `find_forbidden_phrases()` (`tradingagents/utils/safety.py`) before delivery. Outputs that fail the safety check fall back to the deterministic result. All responses include `"not_investment_advice": true`.

## LLM

DeepSeek only. Model alias `deepseek-v4` resolves to `deepseek-v4-flash` (fast mode) or `deepseek-v4-pro` (deep mode). Set `DEEPSEEK_API_KEY` to enable AI synthesis; all endpoints degrade gracefully without it.


<claude-mem-context>
# Memory Context

# [New project] recent context, 2026-05-08 12:44pm GMT+2

No previous sessions found.
</claude-mem-context>
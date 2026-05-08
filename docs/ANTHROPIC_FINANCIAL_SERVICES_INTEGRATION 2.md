# Anthropic Financial Services Integration

IMPERIA adapts research-process ideas from Anthropic's open-source
[`financial-services`](https://github.com/anthropics/financial-services)
examples under the Apache-2.0 license.

The integration is intentionally **methodological**, not infrastructural. IMPERIA
does not vendor Anthropic agents, does not add Anthropic model calls, and does
not require paid financial-data connectors from that repository. Runtime AI
analysis remains DeepSeek-only.

## What Was Adapted

The external repository contains financial-services skills and managed-agent
playbooks for market research, earnings review, valuation review, model
building, competitive analysis, and source-grounded workflow quality control.
IMPERIA adapts those patterns into `tradingagents/expert_agents/skill_pack.py`.

Adapted methods include:

- Event materiality workflow for the News & Event Analyst
- Market-move diagnostics for the Price Action Analyst
- Financial quality triad for the Fundamentals Analyst
- Comps and multiple discipline for the Valuation Analyst
- Filing evidence workflow for the SEC Filings & Regulatory Analyst
- Earnings variance framework for the Earnings Analyst
- Sector and competitive landscape workflow for the Market Context Analyst
- Multi-signal sentiment triangulation for the Market Sentiment Agent
- Risk taxonomy and disconfirming-evidence checks for the Risk Analyst
- Balanced scenario discipline for the Balanced Thesis Agent
- Ownership-signal caveats for insider, Form 4, 13F, and holder analysis
- Research verification workflow for the Research Factors Agent
- Source-grounded note assembly for the Research Synthesizer
- Evidence and source-quality audit checks for the Evidence & Data Quality Auditor

## Where It Is Integrated

Runtime integration points:

- `tradingagents/expert_agents/skill_pack.py` stores the adapted methods,
  source attribution, and admin/API metadata.
- `tradingagents/expert_agents/runtime.py` injects the relevant method block
  into each DeepSeek agent prompt.
- `tradingagents/expert_agents/agents/shared.py` attaches methodology metadata
  to every agent output.
- Agent-output cache keys include the skill-pack version, so method updates do
  not reuse stale analysis.
- `GET /api/admin/agent-methodology` exposes the integration for local/demo
  observability.

## How It Improves IMPERIA

The integration makes the agent graph more disciplined without changing the
stock-first product scope:

- Agents are better at separating material events from noise.
- Valuation analysis now explicitly tracks peer comparability and outlier risk.
- Earnings analysis follows an actual-versus-estimate/prior/guidance framework.
- Market context checks broad-market, sector, peer, and macro layers before
  calling a move company-specific.
- Balanced thesis output includes assumptions and disconfirming evidence.
- Research factors become verification prompts rather than action guidance.
- Evidence auditing surfaces citation, source-quality, stale-data, and provider
  failure issues more clearly.

## Safety Adaptations

Several external examples use investment-banking or equity-research language
that can imply recommendations. IMPERIA does not copy those recommendation
patterns. All adapted methods are constrained by IMPERIA's existing safety
rules:

- Educational research only
- No personalized advice
- No trading or brokerage actions
- No action-oriented recommendation language
- Source-cited claims only
- Missing or stale data must lower confidence and produce warnings

## License And Attribution

The source repository is Apache-2.0. IMPERIA records attribution in
`docs/THIRD_PARTY_NOTICES.md` and exposes source metadata through the admin
methodology endpoint.

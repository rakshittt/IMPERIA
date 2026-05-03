<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

# TradingAgents: Research-Grade Financial Intelligence Platform

TradingAgents is an advanced, AI-powered multi-agent financial research and portfolio assessment framework. Built on LangGraph, it orchestrates a team of specialized, domain-expert LLM personas to forensically analyze portfolios, debate investment theses, and generate institutional-grade quantitative risk matrices.

The system is for research and education. It is not personalized financial advice, automated portfolio management, or an instruction to trade.

## Key Features

- **Domain-Expert AI Agents:** Gone are generic LLM prompts. Each agent embodies a highly specific persona (e.g., CFA Equity Researcher, Behavioral Finance Specialist, Chief Risk Officer, Macro Economist) restricted to its domain expertise.
- **5-Layer Architecture:**
  1. Data Gathering (FMP, Finnhub, YFinance, AlphaVantage, NewsAPI, Tavily)
  2. Expert Analysis (Market, Social, News, Macro, Fundamentals)
  3. Adversarial Debate (Bull vs. Bear Researchers)
  4. Trading & Risk Assessment (Trader Agent & CRO Risk Matrix)
  5. Executive Synthesis (CIO Portfolio Manager)
- **Quantitative Rigor:** Includes 10-dimension risk scoring, conviction metrics (1-100), DuPont decomposition, and information asymmetry detection.
- **Deep-Think Capabilities:** Fully integrated with deep-reasoning models like DeepSeek-v4-pro (via NVIDIA API) for multi-step logical synthesis.
- **Real-Time Web Dashboard:** A responsive, glassmorphism UI for visualizing agent interactions and reading comprehensive markdown reports.

## Agent Architecture

### The Analyst Team
- **Market Quant Analyst**: Analyzes price action, volume profiles, technical indicators, and momentum cross-holdings.
- **Social Behavioral Analyst**: Detects retail sentiment, FOMO/capitulation cycles, crowd psychology, and contrarian signals.
- **News Intelligence Analyst**: Tiers materiality of global news, tracks insider transactions, and builds upcoming catalyst calendars.
- **Macro Economist**: *(NEW)* Classifies macroeconomic regimes, interprets central bank policy, and assesses geopolitical risk.
- **Fundamentals Analyst**: CFA-level forensics evaluating DuPont decomposition, FCF quality, accrual ratios, and balance sheet strength.

### The Research & Debate Team
- **Bull Researcher**: Formulates the positive thesis, scoring conviction across structured evidence pillars.
- **Bear Researcher**: Acts as a forensic risk detective, conducting pre-mortem analysis and identifying hidden fragilities.
- **Head of Research**: Adjudicates the debate, weighting evidence and synthesizing an objective conclusion.

### Trading & Risk Management
- **Trader Agent**: *(NEW)* Translates research into actionable strategy. Provides a conviction score (1-100), risk/reward alignment, and strict tactical monitoring triggers.
- **Chief Risk Officer**: Generates a 10-dimension quantitative risk matrix, stress-testing the portfolio against black-swan scenarios and evaluating user-profile alignment.
- **CIO Portfolio Manager**: Synthesizes all inputs into an executive summary, assigning a final portfolio grade (A+ to F).

## Agent Flow Pipeline

```text
START
 -> Market Analyst | Social Analyst | News Analyst | Macro Economist | Fundamentals Analyst
 -> Bull Researcher <-> Bear Researcher
 -> Research Manager
 -> Trader Agent
 -> Risk Analyst
 -> Portfolio Manager
 -> END
```

## Installation

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
pip install -e .
```

Set your required API keys in a `.env` file (or export them):

```bash
# LLM Providers
DEEPSEEK_API_KEY=...
NVIDIA_API_KEY=...

# Financial Data Vendors
ALPHA_VANTAGE_API_KEY=...
FINANCIAL_MODELING_PREP_API_KEY=...
FINNHUB_API_KEY=...
TWELVE_DATA_API_KEY=...
EODHD_API_KEY=...

# News & Web Search
NEWSAPI_API_KEY=...
NEWSDATA_API_KEY=...
THENEWSAPI_API_TOKEN=...
TAVILY_API_KEY=...
```

*Note: The platform falls back to `yfinance` natively, but the `FinancialKnowledgeBrain` and `NewsKnowledgeBrain` are configured to utilize premium vendors for advanced data.*

## Web UI Dashboard

We built a FastAPI backend with a sleek frontend to interact with the agents. To launch the server:

```bash
uvicorn api:app --reload
```
Navigate to `http://127.0.0.1:8000/` to use the interactive application.

## Python Usage

You can also run the graph directly in Python:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

portfolio = [
    {"ticker": "AAPL", "weight": 0.25, "shares": 10, "cost_basis": 150},
    {"ticker": "MSFT", "weight": 0.20, "shares": 5, "cost_basis": 300},
]

user_profile = {
    "risk_tolerance": "moderate",
    "time_horizon": "3-5 years",
    "goals": "long-term growth",
    "constraints": "avoid high volatility",
}

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
final_state, portfolio_feedback = ta.analyze_portfolio(
    portfolio,
    "2026-05-01",
    user_profile=user_profile,
)

print(portfolio_feedback)
# Access specialized reports via final_state['macro_report'], final_state['trader_report'], etc.
```

## Persistence And Recovery

Each completed run appends portfolio feedback to `~/.tradingagents/memory/portfolio_memory.md`. Future runs inject this historical feedback context directly into the agent prompts. Checkpoint resume is available via the `--checkpoint` flag in the CLI to recover crashed runs.

## Citation

```text
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```

"""Portfolio Feedback Manager: synthesizes research into final portfolio feedback."""

from __future__ import annotations

from tradingagents.agents.schemas import PortfolioFeedback, render_portfolio_feedback
from tradingagents.agents.utils.agent_utils import get_language_instruction
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioFeedback, "Portfolio Feedback Manager")

    def portfolio_manager_node(state) -> dict:
        past_context = state.get("past_context", "")
        lessons_line = (
            f"Prior portfolio feedback context:\n{past_context}\n\n"
            if past_context
            else ""
        )

        # Build the macro and trader report references
        macro_section = ""
        macro_report = state.get("macro_report", "")
        if macro_report:
            macro_section = f"\nMacroeconomic report:\n{macro_report}"

        trader_section = ""
        trader_report = state.get("trader_report", "")
        if trader_report:
            trader_section = f"\nTrader Assessment:\n{trader_report}"

        prompt = f"""You are the **Chief Investment Officer (CIO)** — the final decision-maker. You have 25+ years of portfolio management experience across bull markets, bear markets, and crises. You've managed through the GFC, COVID crash, and multiple rate cycles. You are the most senior person in the room.

## YOUR MISSION
You have received the complete research pipeline output from your team:
- 5 specialist analysts gathered the data
- The research team debated the bull/bear case
- The research manager synthesized the debate
- The trader provided a conviction score and strategy framework
- The risk team stress-tested the portfolio

Now YOU make the final call. Produce the executive portfolio assessment that the user will read.

## COMPLETE EVIDENCE BASE:

Portfolio context:
{state["portfolio_context"]}

{lessons_line}### Specialist Analyst Reports:
- Market (Technical): {state["market_report"]}
- Sentiment: {state["sentiment_report"]}
- News: {state["news_report"]}
- Fundamentals: {state["fundamentals_report"]}{macro_section}

### Research Team Output:
- Bullish Case: {state["bullish_research"]}
- Bearish Case: {state["bearish_research"]}
- Research Synthesis: {state["research_synthesis"]}

### Risk & Strategy:
- Risk Report: {state["risk_report"]}{trader_section}

## YOUR EXECUTIVE ASSESSMENT FRAMEWORK:

### 1. Executive Summary (3-5 sentences)
The single most important paragraph. A busy executive should be able to read ONLY this and understand the portfolio's status.

### 2. The CIO's Verdict
- **Portfolio Grade**: [A+ / A / B+ / B / C+ / C / D / F] — overall quality of the current positioning
- **Conviction Level**: [Very High / High / Moderate / Low / Very Low]
- **Primary Concern**: The #1 thing that keeps you up at night about this portfolio
- **Primary Opportunity**: The #1 thing that excites you about this portfolio

### 3. What Matters Most Right Now
Rank the top 3 factors the user should focus on, in order of importance. For each:
- Why it matters
- What the data shows
- What to watch for

### 4. Comprehensive Assessment
Draw on ALL the analyst reports, research, trader assessment, and risk analysis to provide:
- Market & technical environment impact on the portfolio
- News and event-driven risks/opportunities
- Social sentiment climate and its implications
- Fundamental health assessment
- Macroeconomic positioning
- Risk profile evaluation

### 5. Holding-by-Holding Assessment
For each holding, provide a 3-sentence assessment covering:
- Current fundamental and technical posture
- Key risk and key opportunity
- Forward outlook

### 6. Actionable Monitoring Points
| What to Monitor | Why It Matters | Frequency | Threshold |
|----------------|---------------|-----------|-----------|
(fill with 5-8 specific, measurable monitoring points)

### 7. Recommendations to Consider
Frame as "considerations for the user" — not trade instructions. Example:
- "Consider reviewing exposure to [sector] given [specific concern]"
- "Monitor [metric] — if it crosses [threshold], the risk profile changes materially"
- "The current positioning appears [aligned/misaligned] with the stated [risk tolerance/time horizon]"

### 8. Confidence & Caveats
- Overall confidence in this assessment: [High / Moderate / Low]
- Key caveats and limitations
- What additional information would improve the analysis

### 9. Disclaimer
This analysis is educational research produced by an AI-powered multi-agent system. It is NOT personalized financial advice, investment recommendation, or instruction to buy, sell, or hold any security. Users should consult qualified financial professionals before making investment decisions. Past performance and current analysis do not guarantee future results.{get_language_instruction()}"""

        final_feedback = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_portfolio_feedback,
            "Portfolio Feedback Manager",
        )

        return {"final_portfolio_feedback": final_feedback}

    return portfolio_manager_node

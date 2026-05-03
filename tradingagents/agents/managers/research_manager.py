"""Research Manager: synthesizes the bullish and bearish portfolio debate."""

from __future__ import annotations

from tradingagents.agents.schemas import ResearchSynthesis, render_research_synthesis
from tradingagents.agents.utils.agent_utils import get_language_instruction
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_research_manager(llm):
    structured_llm = bind_structured(llm, ResearchSynthesis, "Research Manager")

    def research_manager_node(state) -> dict:
        debate_state = state["research_debate_state"]
        history = debate_state.get("history", "")

        # Build the macro report reference
        macro_section = ""
        macro_report = state.get("macro_report", "")
        if macro_report:
            macro_section = f"\nMacroeconomic report:\n{macro_report}"

        prompt = f"""You are the **Head of Research** at an institutional investment firm. You are a former Goldman Sachs MD who now runs a 12-person research team. Your job is to adjudicate the bullish vs. bearish debate and produce a definitive portfolio-level research synthesis.

## YOUR MISSION
You have heard both sides of the debate. Now produce the VERDICT — a balanced, evidence-weighted synthesis that:
1. Identifies which side presented the stronger EVIDENCE-BACKED arguments
2. Quantifies the balance of bullish vs. bearish factors
3. Produces a clear conviction assessment with a directional lean
4. Identifies the KEY UNKNOWNS that make the picture uncertain

## EVIDENCE BASE:

Portfolio context:
{state["portfolio_context"]}

Analyst reports:
- Market (Technical): {state["market_report"]}
- Sentiment: {state["sentiment_report"]}
- News: {state["news_report"]}
- Fundamentals: {state["fundamentals_report"]}{macro_section}

Bullish and bearish debate history:
{history}

## SYNTHESIS FRAMEWORK:

### 1. Debate Verdict
- **Winner**: [Bull / Bear / Draw] — who presented the stronger evidence-based case?
- **Margin of Victory**: [Decisive / Narrow / Too Close to Call]
- **Key Differentiator**: What single argument tipped the balance?

### 2. Evidence Weighting
| Factor | Bull Evidence Strength | Bear Evidence Strength | Net Direction |
|--------|----------------------|----------------------|---------------|
| Technicals | [Strong/Moderate/Weak] | [Strong/Moderate/Weak] | [Bull/Bear/Neutral] |
| Fundamentals | [Strong/Moderate/Weak] | [Strong/Moderate/Weak] | [Bull/Bear/Neutral] |
| Sentiment | [Strong/Moderate/Weak] | [Strong/Moderate/Weak] | [Bull/Bear/Neutral] |
| News/Events | [Strong/Moderate/Weak] | [Strong/Moderate/Weak] | [Bull/Bear/Neutral] |
| Macro | [Strong/Moderate/Weak] | [Strong/Moderate/Weak] | [Bull/Bear/Neutral] |

### 3. Conviction Assessment
- **Research Conviction**: [1-10] — how confident is the research in its directional lean?
- **Information Quality**: [High / Medium / Low] — how complete was the data?
- **Consensus vs. Contrarian**: Is the research view consensus or contrarian? (contrarian views need higher evidence bars)

### 4. Key Unknowns & Information Gaps
What COULDN'T be resolved from the available data? What would the research team need to know to increase conviction?

### 5. Implications for Portfolio Management
- What is the SINGLE most important insight for the portfolio manager?
- Where should the portfolio manager focus their attention?
- What is the timeline for the key thesis to play out?

Frame your synthesis as advisory research, not executable instructions. Avoid any trade-execution language.{get_language_instruction()}"""

        research_synthesis = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_research_synthesis,
            "Research Manager",
        )

        new_state = {
            "judge_decision": research_synthesis,
            "history": history,
            "bearish_history": debate_state.get("bearish_history", ""),
            "bullish_history": debate_state.get("bullish_history", ""),
            "current_response": research_synthesis,
            "count": debate_state["count"],
        }

        return {
            "research_debate_state": new_state,
            "research_synthesis": research_synthesis,
        }

    return research_manager_node

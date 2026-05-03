from typing import Annotated, Any

from langgraph.graph import MessagesState
from typing_extensions import TypedDict


class ResearchDebateState(TypedDict):
    bullish_history: Annotated[str, "Bullish portfolio research history"]
    bearish_history: Annotated[str, "Bearish portfolio research history"]
    history: Annotated[str, "Full portfolio research debate history"]
    current_response: Annotated[str, "Latest debate response"]
    judge_decision: Annotated[str, "Research manager synthesis"]
    count: Annotated[int, "Length of the current debate"]


class AgentState(MessagesState):
    user_portfolio: Annotated[list[dict[str, Any]], "User portfolio holdings"]
    user_profile: Annotated[dict[str, Any], "Optional user risk profile"]
    portfolio_context: Annotated[str, "Human-readable portfolio context"]
    portfolio_key: Annotated[str, "Deterministic safe portfolio identifier"]
    analysis_date: Annotated[str, "Date for portfolio analysis"]

    sender: Annotated[str, "Agent that sent this message"]

    # Analyst reports
    market_report: Annotated[str, "Report from the Market Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Sentiment Analyst"]
    news_report: Annotated[str, "Report from the News Intelligence Analyst"]
    fundamentals_report: Annotated[str, "Report from the Fundamentals Analyst"]
    macro_report: Annotated[str, "Report from the Macro Economist"]

    # Research debate and synthesis
    research_debate_state: Annotated[
        ResearchDebateState, "Bullish and bearish portfolio research debate"
    ]
    bullish_research: Annotated[str, "Bullish research case for the portfolio"]
    bearish_research: Annotated[str, "Bearish research case for the portfolio"]
    research_synthesis: Annotated[str, "Research manager portfolio synthesis"]

    # Trader assessment
    trader_report: Annotated[str, "Trader conviction score and strategy assessment"]

    # Risk and final feedback
    risk_report: Annotated[str, "Portfolio risk report"]
    final_portfolio_feedback: Annotated[
        str, "Final portfolio feedback from the Portfolio Feedback Manager"
    ]
    past_context: Annotated[
        str, "Memory log context injected at run start for similar portfolios"
    ]

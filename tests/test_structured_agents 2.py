"""Tests for portfolio-focused structured-output agents."""

from unittest.mock import MagicMock

import pytest

from tradingagents.agents.managers.portfolio_manager import create_portfolio_manager
from tradingagents.agents.managers.research_manager import create_research_manager
from tradingagents.agents.schemas import (
    PortfolioFeedback,
    ResearchSynthesis,
    render_portfolio_feedback,
    render_research_synthesis,
)


def _structured_llm(captured: dict, result):
    structured = MagicMock()
    structured.invoke.side_effect = lambda prompt: (
        captured.__setitem__("prompt", prompt) or result
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm


def _research_state():
    return {
        "portfolio_context": "User portfolio holdings to analyze:\n- ticker=AAPL, weight=60.00%",
        "market_report": "Market report.",
        "sentiment_report": "Sentiment report.",
        "news_report": "News report.",
        "fundamentals_report": "Fundamentals report.",
        "research_debate_state": {
            "history": "Bullish and bearish arguments.",
            "bullish_history": "Bullish case.",
            "bearish_history": "Bearish case.",
            "current_response": "",
            "judge_decision": "",
            "count": 2,
        },
    }


def _portfolio_manager_state(past_context=""):
    state = _research_state()
    state.update(
        {
            "bullish_research": "Bullish case.",
            "bearish_research": "Bearish case.",
            "research_synthesis": "Research synthesis.",
            "risk_report": "Risk report.",
            "past_context": past_context,
        }
    )
    return state


@pytest.mark.unit
class TestRenderPortfolioSchemas:
    def test_research_synthesis_render(self):
        synthesis = ResearchSynthesis(
            overall_research_view="Balanced but quality-skewed.",
            bullish_summary="Cash flow is resilient.",
            bearish_summary="Concentration is elevated.",
            key_portfolio_implications="Monitor exposure and earnings risk.",
        )
        md = render_research_synthesis(synthesis)
        assert "**Overall Research View**" in md
        assert "Cash flow is resilient" in md
        assert "transaction" not in md.lower()

    def test_portfolio_feedback_render_includes_disclaimer(self):
        feedback = _feedback()
        md = render_portfolio_feedback(feedback)
        assert "**Portfolio Recommendation**" in md
        assert "educational research" in md
        assert "not personalized financial advice" in md
        assert ("FINAL " + "TRANSACTION PROPOSAL") not in md


@pytest.mark.unit
class TestResearchManagerAgent:
    def test_structured_path_returns_research_synthesis(self):
        captured = {}
        llm = _structured_llm(
            captured,
            ResearchSynthesis(
                overall_research_view="Constructive with concentration caveats.",
                bullish_summary="Strong fundamentals.",
                bearish_summary="Macro sensitivity.",
                key_portfolio_implications="Review sizing and monitor catalysts.",
            ),
        )
        result = create_research_manager(llm)(_research_state())
        assert "research_synthesis" in result
        assert "Constructive with concentration caveats" in result["research_synthesis"]
        assert "portfolio research" in captured["prompt"].lower()

    def test_fallback_returns_free_text(self):
        llm = MagicMock()
        llm.with_structured_output.side_effect = NotImplementedError("unsupported")
        llm.invoke.return_value = MagicMock(content="Free-text synthesis.")
        result = create_research_manager(llm)(_research_state())
        assert result["research_synthesis"] == "Free-text synthesis."


@pytest.mark.unit
class TestPortfolioFeedbackManagerAgent:
    def test_structured_path_returns_final_portfolio_feedback(self):
        captured = {}
        llm = _structured_llm(captured, _feedback())
        result = create_portfolio_manager(llm)(_portfolio_manager_state())
        assert "final_portfolio_feedback" in result
        assert "educational research" in result["final_portfolio_feedback"]
        assert ("FINAL " + "TRANSACTION PROPOSAL") not in result["final_portfolio_feedback"]
        assert "Risk report." in captured["prompt"]

    def test_past_context_is_optional(self):
        captured = {}
        llm = _structured_llm(captured, _feedback())
        create_portfolio_manager(llm)(_portfolio_manager_state())
        assert "Prior portfolio feedback context" not in captured["prompt"]

        captured = {}
        llm = _structured_llm(captured, _feedback())
        create_portfolio_manager(llm)(
            _portfolio_manager_state(past_context="Prior feedback.")
        )
        assert "Prior portfolio feedback context" in captured["prompt"]
        assert "Prior feedback." in captured["prompt"]


def _feedback():
    return PortfolioFeedback(
        overall_assessment="Quality portfolio with concentration risk.",
        portfolio_recommendation="Review allocation fit and monitor catalysts.",
        bullish_summary="Durable businesses and strong cash flow.",
        bearish_summary="High single-name and macro sensitivity.",
        market_impact="Momentum is mixed.",
        news_impact="Recent news raises monitoring needs.",
        sentiment_impact="Sentiment is constructive but crowded.",
        fundamentals_impact="Fundamentals are solid with valuation caveats.",
        risk_assessment="Volatility and concentration are key risks.",
        diversification_feedback="Diversification could be broader.",
        holding_level_feedback="AAPL dominates portfolio behavior.",
        suggested_actions_to_consider="Consider reviewing concentration and goals.",
        monitoring_points="Earnings, margins, rates, and sentiment.",
        confidence_level="Medium, due to macro uncertainty.",
        disclaimer=(
            "This is educational research, not personalized financial advice "
            "or an instruction to trade."
        ),
    )

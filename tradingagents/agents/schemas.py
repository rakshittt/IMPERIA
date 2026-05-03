"""Pydantic schemas used by portfolio research agents.

The framework's primary artifact is still prose: each agent's natural-language
reasoning is what users read in saved markdown reports and what downstream
agents read as context. Structured output is layered onto the Research Manager
and Portfolio Feedback Manager so their reports keep a consistent shape across
LLM providers while remaining advisory and research-oriented.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PortfolioHolding(BaseModel):
    """A single user portfolio holding."""

    ticker: str = Field(description="Ticker symbol, preserving exchange suffixes.")
    weight: Optional[float] = Field(
        default=None,
        description="Optional portfolio weight as a decimal, e.g. 0.25 for 25%.",
    )
    shares: Optional[float] = Field(
        default=None,
        description="Optional number of shares held.",
    )
    cost_basis: Optional[float] = Field(
        default=None,
        description="Optional average cost basis in the instrument's quote currency.",
    )

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_nonempty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("ticker must be a non-empty string")
        return value.strip().upper()

    @field_validator("weight")
    @classmethod
    def weight_must_be_nonnegative(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("weight must be non-negative")
        return value

    @field_validator("shares", "cost_basis")
    @classmethod
    def numeric_fields_must_be_nonnegative(
        cls, value: Optional[float]
    ) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("shares and cost_basis must be non-negative")
        return value


class UserProfile(BaseModel):
    """Optional user context used to tailor portfolio feedback."""

    risk_tolerance: Optional[str] = Field(default=None)
    time_horizon: Optional[str] = Field(default=None)
    goals: Optional[str] = Field(default=None)
    constraints: Optional[str] = Field(default=None)


class ResearchSynthesis(BaseModel):
    """Portfolio-level synthesis produced by the Research Manager."""

    overall_research_view: str = Field(
        description=(
            "A concise synthesis of the portfolio research debate, including "
            "which arguments carried the most weight and why."
        ),
    )
    bullish_summary: str = Field(
        description="The strongest portfolio-level bullish arguments.",
    )
    bearish_summary: str = Field(
        description="The strongest portfolio-level bearish arguments.",
    )
    key_portfolio_implications: str = Field(
        description=(
            "Practical implications for the user's holdings, exposures, "
            "diversification, and monitoring priorities."
        ),
    )


def render_research_synthesis(synthesis: ResearchSynthesis) -> str:
    """Render a ResearchSynthesis instance to markdown."""
    return "\n".join(
        [
            f"**Overall Research View**: {synthesis.overall_research_view}",
            "",
            f"**Bullish Summary**: {synthesis.bullish_summary}",
            "",
            f"**Bearish Summary**: {synthesis.bearish_summary}",
            "",
            (
                "**Key Portfolio Implications**: "
                f"{synthesis.key_portfolio_implications}"
            ),
        ]
    )


class PortfolioFeedback(BaseModel):
    """Structured portfolio feedback produced by the Portfolio Feedback Manager."""

    overall_assessment: str = Field(
        description="A concise overall assessment of the user's portfolio.",
    )
    portfolio_recommendation: str = Field(
        description=(
            "Research-oriented feedback for the user to consider. Do not frame "
            "this as an executable directive or instruction to transact."
        ),
    )
    bullish_summary: str = Field(description="Positive case for the portfolio.")
    bearish_summary: str = Field(description="Negative case for the portfolio.")
    market_impact: str = Field(
        description="How current market and technical conditions affect holdings.",
    )
    news_impact: str = Field(
        description="How company-specific and macro news affect the portfolio.",
    )
    sentiment_impact: str = Field(
        description="How social and media sentiment affect holdings.",
    )
    fundamentals_impact: str = Field(
        description="How valuation, quality, balance sheet, cash flow, and earnings affect holdings.",
    )
    risk_assessment: str = Field(
        description="Portfolio risk assessment including volatility, correlation, liquidity, and downside scenarios.",
    )
    diversification_feedback: str = Field(
        description="Concentration, sector, geography, and exposure feedback.",
    )
    holding_level_feedback: str = Field(
        description="Holding-by-holding observations and research-backed feedback.",
    )
    suggested_actions_to_consider: str = Field(
        description=(
            "Practical research-oriented actions the user may consider, such as "
            "monitoring, reviewing allocations, or seeking professional advice."
        ),
    )
    monitoring_points: str = Field(
        description="Specific metrics, events, or risks to monitor.",
    )
    confidence_level: str = Field(
        description="Confidence in the analysis, with reasoning and caveats.",
    )
    disclaimer: str = Field(
        description=(
            "Must state that this is educational research and not personalized "
            "financial advice or an instruction to trade."
        ),
    )


def render_portfolio_feedback(feedback: PortfolioFeedback) -> str:
    """Render PortfolioFeedback to markdown for CLI, reports, and memory."""
    return "\n".join(
        [
            f"**Overall Assessment**: {feedback.overall_assessment}",
            "",
            f"**Portfolio Recommendation**: {feedback.portfolio_recommendation}",
            "",
            f"**Bullish Summary**: {feedback.bullish_summary}",
            "",
            f"**Bearish Summary**: {feedback.bearish_summary}",
            "",
            f"**Market Impact**: {feedback.market_impact}",
            "",
            f"**News Impact**: {feedback.news_impact}",
            "",
            f"**Sentiment Impact**: {feedback.sentiment_impact}",
            "",
            f"**Fundamentals Impact**: {feedback.fundamentals_impact}",
            "",
            f"**Risk Assessment**: {feedback.risk_assessment}",
            "",
            f"**Diversification Feedback**: {feedback.diversification_feedback}",
            "",
            f"**Holding-Level Feedback**: {feedback.holding_level_feedback}",
            "",
            (
                "**Suggested Actions To Consider**: "
                f"{feedback.suggested_actions_to_consider}"
            ),
            "",
            f"**Monitoring Points**: {feedback.monitoring_points}",
            "",
            f"**Confidence Level**: {feedback.confidence_level}",
            "",
            f"**Disclaimer**: {feedback.disclaimer}",
        ]
    )

from langchain_core.messages import HumanMessage, RemoveMessage
from pydantic import ValidationError

# Import tools from separate utility files
from tradingagents.agents.schemas import PortfolioHolding, UserProfile
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)


def get_language_instruction() -> str:
    """Return a prompt instruction for the configured output language.

    Returns empty string when English (default), so no extra tokens are used.
    Only applied to user-facing agents (analysts, portfolio manager).
    Internal debate agents stay in English for reasoning quality.
    """
    from tradingagents.dataflows.config import get_config
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


def normalize_portfolio(portfolio: list[dict]) -> list[dict]:
    """Validate and normalize user portfolio holdings."""
    if not isinstance(portfolio, list) or not portfolio:
        raise ValueError("portfolio must be a non-empty list of holdings")
    holdings = []
    errors = []
    for index, item in enumerate(portfolio):
        try:
            holdings.append(PortfolioHolding.model_validate(item).model_dump())
        except ValidationError as exc:
            errors.append(f"holding {index}: {exc}")
    if errors:
        raise ValueError("; ".join(errors))
    return holdings


def normalize_user_profile(user_profile: dict | None) -> dict:
    """Validate and normalize optional user profile data."""
    if user_profile is None:
        return {}
    if not isinstance(user_profile, dict):
        raise ValueError("user_profile must be a mapping when provided")
    return UserProfile.model_validate(user_profile).model_dump(exclude_none=True)


def build_portfolio_context(
    portfolio: list[dict], user_profile: dict | None = None
) -> str:
    """Describe the portfolio so agents preserve tickers and analyze exposure."""
    holdings = normalize_portfolio(portfolio)
    profile = normalize_user_profile(user_profile)

    lines = ["User portfolio holdings to analyze:"]
    for holding in holdings:
        details = [f"ticker={holding['ticker']}"]
        if holding.get("weight") is not None:
            details.append(f"weight={holding['weight']:.2%}")
        if holding.get("shares") is not None:
            details.append(f"shares={holding['shares']}")
        if holding.get("cost_basis") is not None:
            details.append(f"cost_basis={holding['cost_basis']}")
        lines.append(f"- {', '.join(details)}")

    if profile:
        lines.append("User profile:")
        for key in ("risk_tolerance", "time_horizon", "goals", "constraints"):
            if profile.get(key):
                lines.append(f"- {key.replace('_', ' ')}: {profile[key]}")

    lines.append(
        "Use each exact ticker in tool calls, preserving exchange suffixes "
        "(e.g. `.TO`, `.L`, `.HK`, `.T`). Analyze the holdings as a portfolio, "
        "including concentration, diversification, exposure, and user-profile fit."
    )
    return "\n".join(lines)


def build_instrument_context(ticker: str) -> str:
    """Backward-compatible wrapper for single-holding portfolio context."""
    return build_portfolio_context([{"ticker": ticker, "weight": 1.0}])

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add a placeholder so the graph can continue."""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        

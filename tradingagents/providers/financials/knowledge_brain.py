"""Optional free-tier financial vendor aggregation for deep context."""

from __future__ import annotations

import os
from typing import Any

from tradingagents.infra.http import safe_get_json
from tradingagents.utils.validation import normalize_ticker


def get_fmp_data(endpoint: str, symbol: str, **kwargs: Any) -> dict[str, Any] | list[Any] | None:
    """Fetch data from Financial Modeling Prep when an existing key is present."""

    api_key = os.getenv("FINANCIAL_MODELING_PREP_API_KEY")
    if not api_key:
        return None
    ticker = normalize_ticker(symbol)
    return safe_get_json(
        f"https://financialmodelingprep.com/api/v3/{endpoint}/{ticker}",
        params={"apikey": api_key, **kwargs},
        source="fmp",
    )


def get_finnhub_data(endpoint: str, symbol: str, **kwargs: Any) -> dict[str, Any] | list[Any] | None:
    """Fetch data from Finnhub when an existing free-tier key is present."""

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    return safe_get_json(
        f"https://finnhub.io/api/v1/{endpoint}",
        params={"symbol": normalize_ticker(symbol), "token": api_key, **kwargs},
        source="finnhub",
    )


def get_twelve_data(endpoint: str, symbol: str, **kwargs: Any) -> dict[str, Any] | list[Any] | None:
    """Fetch data from Twelve Data when an existing key is present."""

    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return None
    return safe_get_json(
        f"https://api.twelvedata.com/{endpoint}",
        params={"symbol": normalize_ticker(symbol), "apikey": api_key, **kwargs},
        source="twelve_data",
    )


def get_eodhd_data(endpoint: str, symbol: str, **kwargs: Any) -> dict[str, Any] | list[Any] | None:
    """Fetch EODHD free-tier-compatible endpoints when an existing key is present."""

    api_key = os.getenv("EODHD_API_KEY")
    if not api_key:
        return None
    return safe_get_json(
        f"https://eodhistoricaldata.com/api/{endpoint}/{normalize_ticker(symbol)}",
        params={"api_token": api_key, "fmt": "json", **kwargs},
        source="eodhd",
    )


class FinancialKnowledgeBrain:
    """Aggregates optional financial vendors for deep research context."""

    @staticmethod
    def get_income_statement(symbol: str) -> dict[str, Any] | None:
        data = get_fmp_data("income-statement", symbol)
        if data:
            return {"source": "FMP", "data": data}
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Income_Statement")
        return {"source": "EODHD", "data": data} if data else None

    @staticmethod
    def get_balance_sheet(symbol: str) -> dict[str, Any] | None:
        data = get_fmp_data("balance-sheet-statement", symbol)
        if data:
            return {"source": "FMP", "data": data}
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Balance_Sheet")
        return {"source": "EODHD", "data": data} if data else None

    @staticmethod
    def get_cashflow(symbol: str) -> dict[str, Any] | None:
        data = get_fmp_data("cash-flow-statement", symbol)
        if data:
            return {"source": "FMP", "data": data}
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Cash_Flow")
        return {"source": "EODHD", "data": data} if data else None

    @staticmethod
    def get_stock_data(symbol: str) -> dict[str, Any] | None:
        data = get_twelve_data("quote", symbol)
        if data:
            return {"source": "TwelveData", "data": data}
        data = get_finnhub_data("quote", symbol)
        return {"source": "Finnhub", "data": data} if data else None

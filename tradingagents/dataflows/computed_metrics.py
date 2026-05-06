"""Computed valuation and financial metrics using free data sources."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

import tradingagents.dataflows.demo_provider as demo_provider

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _row_value(df: pd.DataFrame | None, labels: list[str], *, sum_last_four: bool = False) -> float | None:
    if df is None or df.empty:
        return None
    for label in labels:
        if label in df.index:
            values = pd.to_numeric(df.loc[label], errors="coerce").dropna()
            if values.empty:
                continue
            if sum_last_four:
                return _safe_float(values.iloc[:4].sum())
            return _safe_float(values.iloc[0])
    return None


def _info_value(info: dict[str, Any], labels: list[str]) -> float | None:
    for label in labels:
        value = _safe_float(info.get(label))
        if value is not None:
            return value
    return None


def _sec_fallback(ticker: str) -> dict[str, Any] | None:
    try:
        from tradingagents.dataflows.sec_edgar import get_xbrl_financials

        return get_xbrl_financials(ticker)
    except Exception:
        return None


def compute_financial_metrics(ticker: str, *, include_sec_fallback: bool = True) -> dict[str, Any]:
    """Compute common ratios from yfinance statements with SEC fallback."""

    warnings: list[str] = []
    symbol = ticker.upper().strip()
    if demo_provider.is_demo_mode():
        demo_metrics = demo_provider.get_demo_metrics(symbol)
        if demo_metrics:
            return demo_metrics
    try:
        import yfinance as yf

        stock = yf.Ticker(symbol)
        info = stock.info or {}
        quarterly_income = getattr(stock, "quarterly_income_stmt", None)
        quarterly_balance = getattr(stock, "quarterly_balance_sheet", None)
        quarterly_cashflow = getattr(stock, "quarterly_cashflow", None)
    except Exception as exc:
        logger.exception("yfinance metrics fetch failed for %s", symbol)
        info = {}
        quarterly_income = quarterly_balance = quarterly_cashflow = None
        warnings.append(f"yfinance metrics unavailable: {exc}")

    revenue_ttm = _row_value(
        quarterly_income,
        ["Total Revenue", "Operating Revenue", "Revenue"],
        sum_last_four=True,
    ) or _info_value(info, ["totalRevenue"])
    gross_profit_ttm = _row_value(quarterly_income, ["Gross Profit"], sum_last_four=True)
    operating_income_ttm = _row_value(quarterly_income, ["Operating Income"], sum_last_four=True)
    net_income_ttm = _row_value(
        quarterly_income,
        ["Net Income", "Net Income Common Stockholders"],
        sum_last_four=True,
    ) or _info_value(info, ["netIncomeToCommon"])
    operating_cash_flow_ttm = _row_value(
        quarterly_cashflow,
        ["Operating Cash Flow", "Total Cash From Operating Activities"],
        sum_last_four=True,
    )
    capex_ttm = _row_value(
        quarterly_cashflow,
        ["Capital Expenditure", "Capital Expenditures"],
        sum_last_four=True,
    )
    free_cash_flow_ttm = _info_value(info, ["freeCashflow"])
    if free_cash_flow_ttm is None and operating_cash_flow_ttm is not None:
        free_cash_flow_ttm = operating_cash_flow_ttm + (capex_ttm or 0)

    assets = _row_value(quarterly_balance, ["Total Assets"])
    current_assets = _row_value(quarterly_balance, ["Current Assets", "Total Current Assets"])
    current_liabilities = _row_value(
        quarterly_balance, ["Current Liabilities", "Total Current Liabilities"]
    )
    inventory = _row_value(quarterly_balance, ["Inventory"])
    equity = _row_value(
        quarterly_balance,
        ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"],
    )
    total_debt = _row_value(quarterly_balance, ["Total Debt"]) or _info_value(info, ["totalDebt"])
    cash = _row_value(
        quarterly_balance,
        ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    )
    ebitda = _info_value(info, ["ebitda"])
    enterprise_value = _info_value(info, ["enterpriseValue"])
    market_cap = _info_value(info, ["marketCap"])

    if include_sec_fallback and revenue_ttm is None:
        sec_data = _sec_fallback(symbol)
        if sec_data:
            annual = sec_data.get("annual", {})
            revenue_ttm = _safe_float((annual.get("revenue") or {}).get("value"))
            net_income_ttm = net_income_ttm or _safe_float((annual.get("net_income") or {}).get("value"))
            assets = assets or _safe_float((annual.get("assets") or {}).get("value"))
            equity = equity or _safe_float((annual.get("stockholders_equity") or {}).get("value"))
            warnings.append("Some metrics used SEC annual XBRL fallback where yfinance data was missing.")

    metrics = {
        "pe": _info_value(info, ["trailingPE"]) or _ratio(market_cap, net_income_ttm),
        "forward_pe": _info_value(info, ["forwardPE"]),
        "peg": _info_value(info, ["pegRatio", "trailingPegRatio"]),
        "eps": _info_value(info, ["trailingEps"]),
        "revenue_growth": _info_value(info, ["revenueGrowth"]),
        "gross_margin": _info_value(info, ["grossMargins"]) or _ratio(gross_profit_ttm, revenue_ttm),
        "operating_margin": _info_value(info, ["operatingMargins"]) or _ratio(operating_income_ttm, revenue_ttm),
        "net_margin": _info_value(info, ["profitMargins"]) or _ratio(net_income_ttm, revenue_ttm),
        "roe": _info_value(info, ["returnOnEquity"]) or _ratio(net_income_ttm, equity),
        "roa": _info_value(info, ["returnOnAssets"]) or _ratio(net_income_ttm, assets),
        "debt_to_equity": _info_value(info, ["debtToEquity"])
        or ((total_debt / equity * 100) if total_debt is not None and equity not in (None, 0) else None),
        "current_ratio": _info_value(info, ["currentRatio"]) or _ratio(current_assets, current_liabilities),
        "quick_ratio": _ratio(
            (current_assets - inventory) if current_assets is not None and inventory is not None else None,
            current_liabilities,
        ),
        "free_cash_flow_margin": _ratio(free_cash_flow_ttm, revenue_ttm),
        "ev_to_ebitda": _info_value(info, ["enterpriseToEbitda"]) or _ratio(enterprise_value, ebitda),
    }
    formulas = {
        "pe": "market_cap / trailing_twelve_month_net_income",
        "forward_pe": "provider forward P/E estimate when available",
        "gross_margin": "ttm_gross_profit / ttm_revenue",
        "operating_margin": "ttm_operating_income / ttm_revenue",
        "net_margin": "ttm_net_income / ttm_revenue",
        "roe": "ttm_net_income / stockholders_equity",
        "roa": "ttm_net_income / total_assets",
        "debt_to_equity": "total_debt / stockholders_equity",
        "current_ratio": "current_assets / current_liabilities",
        "quick_ratio": "(current_assets - inventory) / current_liabilities",
        "free_cash_flow_margin": "ttm_free_cash_flow / ttm_revenue",
        "ev_to_ebitda": "enterprise_value / EBITDA",
    }
    missing = [name for name, value in metrics.items() if value is None]
    if missing:
        warnings.append("Unavailable metric inputs: " + ", ".join(sorted(missing)) + ".")
    ttm = {
        "revenue": revenue_ttm,
        "gross_profit": gross_profit_ttm,
        "operating_income": operating_income_ttm,
        "net_income": net_income_ttm,
        "operating_cash_flow": operating_cash_flow_ttm,
        "capital_expenditures": capex_ttm,
        "free_cash_flow": free_cash_flow_ttm,
    }
    return {
        "ticker": symbol,
        "profile": {
            key: value
            for key, value in {
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": market_cap,
            }.items()
            if value is not None
        },
        "metrics": metrics,
        "ttm": ttm,
        "balance_sheet_snapshot": {
            key: value
            for key, value in {
                "assets": assets,
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "equity": equity,
                "total_debt": total_debt,
                "cash": cash,
            }.items()
            if value is not None
        },
        "warnings": warnings,
        "sources": ["yfinance", "SEC XBRL fallback" if include_sec_fallback else ""],
        "formula_metadata": formulas,
        "citations": [
            {
                "source_type": "market_data",
                "provider": "yfinance",
                "title": f"{symbol} financial statements via yfinance",
                "url": f"https://finance.yahoo.com/quote/{symbol}/financials",
                "ticker": symbol,
            }
        ],
    }


def get_structured_ratios(ticker: str) -> dict[str, Any]:
    """Compatibility wrapper for routes and tools."""

    return compute_financial_metrics(ticker)

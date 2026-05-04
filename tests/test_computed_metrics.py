import pandas as pd
import pytest

from tradingagents.dataflows.computed_metrics import compute_financial_metrics


class FakeTicker:
    info = {
        "marketCap": 200,
        "trailingPE": 10,
        "forwardPE": 9,
        "trailingEps": 2,
        "totalDebt": 50,
        "freeCashflow": 12,
    }
    quarterly_income_stmt = pd.DataFrame(
        [[25, 25, 25, 25], [10, 10, 10, 10], [8, 8, 8, 8], [5, 5, 5, 5]],
        index=["Total Revenue", "Gross Profit", "Operating Income", "Net Income"],
    )
    quarterly_balance_sheet = pd.DataFrame(
        [[100], [40], [20], [5], [50], [50]],
        index=["Total Assets", "Current Assets", "Current Liabilities", "Inventory", "Stockholders Equity", "Total Debt"],
    )
    quarterly_cashflow = pd.DataFrame(
        [[20, 20, 20, 20], [-3, -3, -3, -3]],
        index=["Operating Cash Flow", "Capital Expenditure"],
    )


@pytest.mark.unit
def test_compute_financial_metrics_from_yfinance(monkeypatch):
    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda ticker: FakeTicker())
    data = compute_financial_metrics("AAPL", include_sec_fallback=False)
    assert data["ttm"]["revenue"] == 100
    assert data["metrics"]["pe"] == 10
    assert data["metrics"]["gross_margin"] == 0.4
    assert data["metrics"]["current_ratio"] == 2

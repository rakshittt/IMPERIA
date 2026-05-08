from unittest.mock import MagicMock

import pytest

from tradingagents.agents.analysts.earnings_analyst import create_earnings_analyst
from tradingagents.agents.analysts.macro_analyst import create_macro_context_agent
from tradingagents.agents.analysts.sec_filings_analyst import create_sec_filings_analyst


def _state():
    return {
        "user_portfolio": [{"ticker": "AAPL", "weight": 1}],
        "portfolio_context": "AAPL 100%",
        "analysis_date": "2026-01-01",
        "portfolio_key": "AAPL",
    }


@pytest.mark.unit
def test_sec_filings_analyst_with_mocked_data(monkeypatch):
    monkeypatch.setattr("tradingagents.agents.analysts.sec_filings_analyst.get_sec_filings", lambda ticker, limit=12: [{"filing_type": "10-K", "url": "u"}])
    monkeypatch.setattr("tradingagents.agents.analysts.sec_filings_analyst.get_xbrl_financials", lambda ticker: {"annual": {}})
    monkeypatch.setattr("tradingagents.agents.analysts.sec_filings_analyst.get_form4_insider_trades", lambda ticker, limit=10: [])
    monkeypatch.setattr("tradingagents.agents.analysts.sec_filings_analyst.get_13f_related_filings", lambda ticker, limit=10: {})
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="SEC synthesis")
    result = create_sec_filings_analyst(llm)(_state())
    assert result["sec_filings_report"]["summary"] == "SEC synthesis"


@pytest.mark.unit
def test_sec_filings_analyst_graceful_failure(monkeypatch):
    monkeypatch.setattr("tradingagents.agents.analysts.sec_filings_analyst.get_sec_filings", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad")))
    result = create_sec_filings_analyst(MagicMock())(_state())
    assert result["sec_filings_report"]["warnings"]


@pytest.mark.unit
def test_macro_context_agent_with_mocked_data(monkeypatch):
    monkeypatch.setattr("tradingagents.agents.analysts.macro_analyst.get_market_breadth", lambda: _dump({"advancing": 5, "declining": 1}))
    monkeypatch.setattr("tradingagents.agents.analysts.macro_analyst.get_market_indices", lambda: [_dump({"ticker": "SPY"})])
    monkeypatch.setattr("tradingagents.agents.analysts.macro_analyst.get_sector_performance", lambda: [_dump({"sector": "Technology", "change_pct": 2})])
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Macro synthesis")
    result = create_macro_context_agent(llm)(_state())
    assert result["macro_context_report"]["macro_signal"] == "risk_on"
    assert result["macro_context_report"]["summary"] == "Macro synthesis"


@pytest.mark.unit
def test_earnings_analyst_with_mocked_data(monkeypatch):
    monkeypatch.setattr("tradingagents.agents.analysts.earnings_analyst.get_next_earnings", lambda ticker: _dump({"ticker": ticker, "report_date": "2026-01-01"}))
    monkeypatch.setattr("tradingagents.agents.analysts.earnings_analyst.get_earnings_history", lambda ticker, limit=8: [_dump({"beat_miss": "beat"})])
    monkeypatch.setattr("tradingagents.agents.analysts.earnings_analyst.get_earnings_surprise_stats", lambda ticker: _dump({"quarters": 1, "beat_rate": 1}))
    monkeypatch.setattr("tradingagents.agents.analysts.earnings_analyst.get_earnings_news", lambda ticker: [])
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="Earnings synthesis")
    result = create_earnings_analyst(llm)(_state())
    assert result["earnings_report"]["summary"] == "Earnings synthesis"


@pytest.mark.unit
def test_earnings_analyst_graceful_failure(monkeypatch):
    monkeypatch.setattr("tradingagents.agents.analysts.earnings_analyst.get_next_earnings", lambda ticker: (_ for _ in ()).throw(RuntimeError("bad")))
    result = create_earnings_analyst(MagicMock())(_state())
    assert result["earnings_report"]["warnings"]


class _dump:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload

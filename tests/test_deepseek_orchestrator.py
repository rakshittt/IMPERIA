import pytest
import asyncio

from tradingagents.engine.deepseek_orchestrator import ContextBundle, DeepSeekContextOrchestrator


@pytest.mark.unit
def test_build_fast_context_fields(monkeypatch):
    orchestrator = DeepSeekContextOrchestrator()
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.market_data.get_quote", lambda ticker: _dump({"ticker": ticker, "price": 1}))
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator._profile_from_yfinance", lambda ticker: {"ticker": ticker, "name": "Apple"})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.compute_financial_metrics", lambda ticker: {"metrics": {"pe": 10}})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.news_aggregator.get_stock_news", lambda ticker, limit=5: [_dump({"title": "News"})])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.earnings_data.get_next_earnings", lambda ticker: _dump({"ticker": ticker, "report_date": "2026-01-01"}))
    bundle = asyncio.run(orchestrator.build_fast_context("aapl", "question"))
    assert bundle.ticker == "AAPL"
    assert bundle.quote["price"] == 1
    assert bundle.news[0]["title"] == "News"


@pytest.mark.unit
def test_build_deep_context_timeout_fallback(monkeypatch):
    orchestrator = DeepSeekContextOrchestrator()
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.market_data.get_quote", lambda ticker: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator._profile_from_yfinance", lambda ticker: {})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.compute_financial_metrics", lambda ticker: {})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.news_aggregator.get_stock_news", lambda ticker, limit=20: [])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.earnings_data.get_next_earnings", lambda ticker: None)
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.earnings_data.get_earnings_history", lambda ticker, limit=8: [])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.get_sec_filings", lambda ticker, filing_type=None, limit=10: [])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.get_xbrl_financials", lambda ticker: {})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.get_form4_insider_trades", lambda ticker, limit=25: [])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.get_13f_related_filings", lambda ticker, limit=25: {})
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.market_data.get_market_breadth", lambda: _dump({}))
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.market_data.get_sector_performance", lambda: [])
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.FinancialKnowledgeBrain.get_income_statement", lambda ticker: None)
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.FinancialKnowledgeBrain.get_balance_sheet", lambda ticker: None)
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.FinancialKnowledgeBrain.get_cashflow", lambda ticker: None)
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.FinancialKnowledgeBrain.get_stock_data", lambda ticker: None)
    monkeypatch.setattr("tradingagents.engine.deepseek_orchestrator.NewsKnowledgeBrain.web_search", lambda query: None)
    bundle = asyncio.run(orchestrator.build_deep_context("AAPL", "question"))
    assert isinstance(bundle, ContextBundle)
    assert any("quote unavailable" in warning for warning in bundle.warnings)


@pytest.mark.unit
def test_format_for_prompt_omits_nulls():
    text = DeepSeekContextOrchestrator().format_for_prompt(ContextBundle(ticker="AAPL", query="q", quote={"price": 1}))
    assert '"quote"' in text
    assert "next_earnings" not in text


@pytest.mark.unit
def test_invalid_ticker_rejected():
    with pytest.raises(ValueError):
        asyncio.run(DeepSeekContextOrchestrator().build_fast_context("BTC-USD", "q"))


class _dump:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self):
        return self.payload

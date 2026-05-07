import pytest
from pydantic import ValidationError

from tradingagents.cache.keys import agent_cache_key
from tradingagents.expert_agents.agents import evidence_auditor, fundamentals
from tradingagents.expert_agents import runtime as runtime_module
from tradingagents.expert_agents.planner import plan_query, selected_agents_for_intent
from tradingagents.expert_agents.runtime import ExpertAgentRuntime
from tradingagents.schemas.agent_output import BaseAgentOutput
from tradingagents.utils.safety import find_forbidden_phrases, validate_sentiment_label


def _bundle():
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "intent": "fundamentals",
        "window": "today",
        "metrics": {
            "metrics": {"revenue_growth": 0.08, "net_margin": 0.24, "roe": 0.5, "free_cash_flow_margin": 0.22, "pe": 28},
            "ttm": {"revenue": 100},
            "warnings": [],
        },
        "citations": [
            {
                "id": "c_yf_aapl_001",
                "citation_id": "c_yf_aapl_001",
                "source_type": "financial",
                "provider": "yfinance",
                "title": "AAPL metrics",
                "url": "https://example.com",
            }
        ],
        "warnings": [],
        "provider_metadata": [{"source": "yfinance", "status": "ok"}],
    }


@pytest.mark.unit
def test_deterministic_planner_keeps_simple_lookup_zero_agent():
    plan = plan_query("What is Apple P/E?", selected_ticker="AAPL")
    assert plan.intent == "simple_lookup"
    assert selected_agents_for_intent(plan.intent, "fast") == []


@pytest.mark.unit
def test_planner_selects_expected_fast_agents():
    plan = plan_query("Why is NVDA moving today?", selected_ticker="NVDA")
    assert plan.intent == "why_moving"
    agents = selected_agents_for_intent(plan.intent, "fast")
    assert agents == ["news_event", "price_action", "market_context", "sentiment", "synthesizer", "evidence_auditor"]
    assert len(agents) <= 7


@pytest.mark.unit
def test_planner_selects_broad_deep_panel():
    agents = selected_agents_for_intent("deep_research", "deep")
    assert "insider_activity" in agents
    assert "research_factors" in agents
    assert "evidence_auditor" in agents
    assert len(agents) == 14


@pytest.mark.unit
def test_agent_output_schema_rejects_unknown_fields():
    payload = fundamentals.run(_bundle())
    assert BaseAgentOutput.model_validate({k: payload[k] for k in BaseAgentOutput.model_fields})
    with pytest.raises(ValidationError):
        BaseAgentOutput.model_validate({**{k: payload[k] for k in BaseAgentOutput.model_fields}, "extra": "nope"})


@pytest.mark.unit
def test_missing_data_agent_returns_stub_like_warning():
    payload = fundamentals.run({**_bundle(), "metrics": {"metrics": {}, "warnings": ["Unavailable metric inputs: pe."]}})
    assert payload["confidence_score"] <= 25
    assert payload["warnings"]


@pytest.mark.unit
def test_evidence_auditor_catches_fabricated_citation_and_advice():
    bundle = _bundle()
    upstream = {
        "synthesizer": {
            "executive_summary": "Revenue grew [cit:c_fake_999]. You should buy.",
            "warnings": [],
        }
    }
    audit = evidence_auditor.run(bundle, upstream)
    assert "c_fake_999" in audit["fabricated_citation_ids"]
    assert audit["advice_language_violations"]
    assert audit["final_answer_safe"] is False


@pytest.mark.unit
def test_safety_labels_and_forbidden_phrases():
    assert find_forbidden_phrases("You should buy this stock.")
    assert validate_sentiment_label("bullish")
    assert not validate_sentiment_label("strong-buy")


@pytest.mark.unit
def test_agent_cache_key_includes_input_data_hash():
    left = agent_cache_key("fundamentals", "AAPL", "fundamentals", "today", {"price": 1})
    right = agent_cache_key("fundamentals", "AAPL", "fundamentals", "today", {"price": 2})
    assert left != right
    assert left.startswith("agent:fundamentals:AAPL:fundamentals:today:")


@pytest.mark.unit
def test_runtime_uses_selected_agents_without_live_data(monkeypatch):
    runtime = ExpertAgentRuntime()
    monkeypatch.setattr(runtime, "assemble_evidence_bundle", lambda ticker, query, intent, window: _bundle() | {"intent": intent, "window": window, "query": query})
    result = runtime.run(query="What are AAPL fundamentals?", ticker="AAPL", mode="fast")
    assert result.intent == "fundamentals"
    assert set(result.agent_outputs).issuperset({"fundamentals", "valuation", "sec_filings", "risk", "synthesizer", "evidence_auditor"})
    assert result.not_investment_advice is True


@pytest.mark.unit
def test_placeholder_deepseek_key_does_not_call_llm(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "placeholder")
    monkeypatch.setattr(runtime_module, "deepseek_text", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call DeepSeek")))
    runtime = ExpertAgentRuntime()
    payload = runtime.run_agent("fundamentals", _bundle(), {}, mode="fast")
    assert payload["agent_name"] == "Fundamentals Analyst"

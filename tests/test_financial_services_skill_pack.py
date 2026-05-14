import json

import pytest
from fastapi.testclient import TestClient

from tradingagents.api.main import create_app
from tradingagents.expert_agents import runtime as runtime_module
from tradingagents.expert_agents.agents import fundamentals
from tradingagents.core.agents.skill_pack import (
    METHODS_BY_AGENT,
    SKILL_PACK_VERSION,
    agent_method_prompt,
    agent_methods_for_response,
    methodology_for_agent,
)
from tradingagents.persistence import db as db_module
from tradingagents.persistence.db import PersistenceDB
from tradingagents.utils.safety import find_forbidden_phrases
from tradingagents.infra.llm.deepseek import resolve_deepseek_model


def _bundle():
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "intent": "fundamentals",
        "window": "today",
        "metrics": {
            "metrics": {
                "revenue_growth": 0.08,
                "net_margin": 0.24,
                "roe": 0.5,
                "free_cash_flow_margin": 0.22,
                "pe": 28,
            },
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
def test_skill_pack_exposes_source_attribution_and_all_agent_methods():
    response = agent_methods_for_response()
    assert response["skill_pack_version"] == SKILL_PACK_VERSION
    assert response["source_attribution"]["license"] == "Apache-2.0"
    assert response["source_attribution"]["url"] == "https://github.com/anthropics/financial-services"
    assert set(METHODS_BY_AGENT).issubset(response["agents"])


@pytest.mark.unit
def test_skill_pack_method_prompts_are_safe_and_agent_specific():
    text = agent_method_prompt("valuation")
    assert "comps and multiple discipline" in text
    assert not find_forbidden_phrases(text)
    assert methodology_for_agent("Fundamentals Analyst")["methodology"] == "financial quality triad"


@pytest.mark.unit
def test_agent_output_includes_methodology_metadata():
    payload = fundamentals.run(_bundle())
    assert payload["methodology"]["skill_pack_version"] == SKILL_PACK_VERSION
    assert payload["methodology"]["methodology"] == "financial quality triad"
    assert payload["quality_checks"]
    assert payload["source_quality_notes"]


@pytest.mark.unit
def test_deepseek_refinement_prompt_includes_adapted_method(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-real-looking")
    monkeypatch.setenv("IMPERIA_AGENT_LLM_REFINEMENT", "all")
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    captured = {}

    def fake_deepseek_text(messages, **kwargs):
        captured["system"] = messages[0]["content"]
        return json.dumps(fundamentals.run(_bundle()))

    monkeypatch.setattr(runtime_module, "deepseek_text", fake_deepseek_text)
    runtime = runtime_module.ExpertAgentRuntime()
    monkeypatch.setattr(runtime.cache, "get", lambda key: None)
    monkeypatch.setattr(runtime.cache, "set", lambda *args, **kwargs: None)
    payload = runtime.run_agent("fundamentals", _bundle(), {}, mode="fast")
    assert payload["agent_name"] == "Fundamentals Analyst"
    assert "ADAPTED INSTITUTIONAL RESEARCH METHOD" in captured["system"]
    assert "financial quality triad" in captured["system"]


@pytest.mark.unit
def test_admin_agent_methodology_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSISTENCE_DB_PATH", str(tmp_path / "user.db"))
    monkeypatch.setenv("TRADINGAGENTS_SQLITE_CACHE", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setattr(db_module, "_DB", PersistenceDB(tmp_path / "user.db"))
    client = TestClient(create_app())
    payload = client.get("/api/admin/agent-methodology").json()
    assert payload["success"] is True
    assert payload["data"]["source_attribution"]["license"] == "Apache-2.0"
    assert "valuation" in payload["data"]["agents"]


@pytest.mark.unit
def test_deepseek_v4_alias_resolves_to_api_models(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4")
    monkeypatch.delenv("DEEPSEEK_FAST_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_DEEP_MODEL", raising=False)
    assert resolve_deepseek_model("fast") == "deepseek-v4-flash"
    assert resolve_deepseek_model("deep") == "deepseek-v4-pro"

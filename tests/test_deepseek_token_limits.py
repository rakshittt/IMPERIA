import pytest

from tradingagents.utils import deepseek


@pytest.mark.unit
def test_deepseek_chat_omits_max_tokens_by_default(monkeypatch):
    captured = {}

    def fake_post_json(*args, json_payload, **kwargs):
        captured["payload"] = json_payload
        return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-real-looking")
    monkeypatch.setenv("DEEPSEEK_CALLS_PER_MINUTE", "1000")
    monkeypatch.setattr(deepseek, "safe_post_json", fake_post_json)
    deepseek._hits.clear()

    payload = deepseek.deepseek_chat([{"role": "user", "content": "hello"}])

    assert payload is not None
    assert "max_tokens" not in captured["payload"]


@pytest.mark.unit
def test_deepseek_chat_keeps_explicit_max_tokens_override(monkeypatch):
    captured = {}

    def fake_post_json(*args, json_payload, **kwargs):
        captured["payload"] = json_payload
        return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-real-looking")
    monkeypatch.setenv("DEEPSEEK_CALLS_PER_MINUTE", "1000")
    monkeypatch.setattr(deepseek, "safe_post_json", fake_post_json)
    deepseek._hits.clear()

    payload = deepseek.deepseek_chat([{"role": "user", "content": "hello"}], max_tokens=123)

    assert payload is not None
    assert captured["payload"]["max_tokens"] == 123

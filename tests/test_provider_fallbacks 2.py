import pytest

from tradingagents.dataflows import free_provider_fallbacks as fallbacks


@pytest.mark.unit
def test_finnhub_quote_uses_env_without_exposing_key(monkeypatch):
    captured = {}
    monkeypatch.setenv("FINNHUB_API_KEY", "secret-token")

    def fake_get(url, params, timeout):
        captured["params"] = params

        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"c": 101, "pc": 100, "d": 1, "dp": 1, "o": 99, "h": 102, "l": 98}

        return Response()

    monkeypatch.setattr(fallbacks.requests, "get", fake_get)
    quote = fallbacks.get_finnhub_quote("AAPL")
    assert quote["price"] == 101
    assert captured["params"]["token"] == "secret-token"
    assert "secret-token" not in str(quote)


@pytest.mark.unit
def test_alpha_vantage_overview_normalizes_numbers(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "secret-token")

    def fake_get(url, params, timeout):
        class Response:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "Symbol": "AAPL",
                    "Name": "Apple Inc.",
                    "Exchange": "NASDAQ",
                    "Sector": "Technology",
                    "MarketCapitalization": "12345",
                    "PERatio": "20.5",
                }

        return Response()

    monkeypatch.setattr(fallbacks.requests, "get", fake_get)
    profile = fallbacks.get_alpha_vantage_overview("AAPL")
    assert profile["market_cap"] == 12345
    assert profile["pe"] == 20.5

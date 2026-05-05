import pytest

from tradingagents.cache.sqlite_cache import SQLiteCache
from tradingagents.dataflows import news_aggregator


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    monkeypatch.setattr(news_aggregator, "get_default_cache", lambda: cache)
    return cache


@pytest.mark.unit
def test_finnhub_company_news(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "key")
    monkeypatch.setattr(news_aggregator, "_get_json", lambda url, params: [{"headline": "AAPL beats", "url": "u", "datetime": 1, "summary": "s"}])
    assert news_aggregator._finnhub_company_news("AAPL")[0].title == "AAPL beats"


@pytest.mark.unit
def test_newsapi_search(monkeypatch):
    monkeypatch.setenv("NEWSAPI_API_KEY", "key")
    monkeypatch.setattr(news_aggregator, "_get_json", lambda url, params: {"articles": [{"title": "Market", "url": "u", "source": {"name": "Reuters"}}]})
    assert news_aggregator._newsapi_search("stocks")[0].source == "Reuters"


@pytest.mark.unit
def test_newsdata_and_thenewsapi(monkeypatch):
    monkeypatch.setenv("NEWSDATA_API_KEY", "key")
    monkeypatch.setenv("THENEWSAPI_COM_API_TOKEN", "key")
    monkeypatch.setattr(news_aggregator, "_get_json", lambda url, params: {"results": [{"title": "Business", "link": "u"}]} if "newsdata" in url else {"data": [{"title": "Tape", "url": "v"}]})
    assert news_aggregator._newsdata_search("stocks")[0].title == "Business"
    assert news_aggregator._thenewsapi_search("stocks")[0].title == "Tape"


@pytest.mark.unit
def test_search_news_dedupes_and_sorts(cache, monkeypatch):
    items = [
        news_aggregator.NewsItem(title="Same title long", url="u1", source="A", published_at="2026-01-02T00:00:00+00:00"),
        news_aggregator.NewsItem(title="Same title long duplicate", url="u2", source="B", published_at="2026-01-03T00:00:00+00:00"),
        news_aggregator.NewsItem(title="Different", url="u3", source="C", published_at="2026-01-01T00:00:00+00:00"),
    ]
    monkeypatch.setattr(news_aggregator, "_newsapi_search", lambda q: items)
    monkeypatch.setattr(news_aggregator, "_newsdata_search", lambda q: [])
    monkeypatch.setattr(news_aggregator, "_thenewsapi_search", lambda q: [])
    result = news_aggregator.search_news("x", limit=5)
    assert [item.title for item in result] == ["Same title long duplicate", "Different"]
    assert result[0].citation_id == "news-1"


@pytest.mark.unit
def test_unicode_title_deduplication(cache, monkeypatch):
    items = [
        news_aggregator.NewsItem(title="ＡＡＰＬ beats estimates", url="u1", source="A", published_at="2026-01-02T00:00:00+00:00"),
        news_aggregator.NewsItem(title="AAPL beats estimates again", url="u2", source="B", published_at="2026-01-03T00:00:00+00:00"),
    ]
    monkeypatch.setattr(news_aggregator, "_newsapi_search", lambda q: items)
    monkeypatch.setattr(news_aggregator, "_newsdata_search", lambda q: [])
    monkeypatch.setattr(news_aggregator, "_thenewsapi_search", lambda q: [])
    assert len(news_aggregator.search_news("aapl", limit=10)) == 1


@pytest.mark.unit
def test_all_news_sources_fail_returns_empty(cache, monkeypatch):
    monkeypatch.setattr(news_aggregator, "_newsapi_search", lambda q: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr(news_aggregator, "_newsdata_search", lambda q: (_ for _ in ()).throw(RuntimeError("bad")))
    monkeypatch.setattr(news_aggregator, "_thenewsapi_search", lambda q: (_ for _ in ()).throw(RuntimeError("bad")))
    assert news_aggregator.search_news("aapl") == []


@pytest.mark.unit
def test_get_stock_news_merges_yfinance(cache, monkeypatch):
    monkeypatch.setattr(news_aggregator, "_finnhub_company_news", lambda ticker: [])
    monkeypatch.setattr(news_aggregator, "search_news", lambda query, limit=40: [])
    monkeypatch.setattr(news_aggregator, "_yfinance_news", lambda ticker, limit: [news_aggregator.NewsItem(title="YF", source="Yahoo", tickers_mentioned=[ticker])])
    assert news_aggregator.get_stock_news("AAPL", limit=5)[0].source == "Yahoo"

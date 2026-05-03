import os
import requests
from typing import Dict, Any, Optional

def get_newsapi_news(query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from NewsAPI."""
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return None
    url = "https://newsapi.org/v2/everything"
    params = {"q": query, "apiKey": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
        return None

def get_newsdata_news(query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from NewsData.io."""
    api_key = os.getenv("NEWSDATA_API_KEY")
    if not api_key:
        return None
    url = "https://newsdata.io/api/1/news"
    params = {"q": query, "apikey": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from NewsData: {e}")
        return None

def get_thenewsapi_news(query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from TheNewsAPI."""
    api_key = os.getenv("THENEWSAPI_API_TOKEN")
    if not api_key:
        return None
    url = "https://api.thenewsapi.com/v1/news/all"
    params = {"search": query, "api_token": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from TheNewsAPI: {e}")
        return None

def search_tavily(query: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from Tavily Search API."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return None
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {"api_key": api_key, "query": query, "search_depth": "advanced", **kwargs}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from Tavily: {e}")
        return None

class NewsKnowledgeBrain:
    """Aggregates multiple news data vendors and web search APIs."""
    
    @staticmethod
    def get_company_news(symbol: str) -> Optional[Dict[str, Any]]:
        # Try NewsAPI first
        data = get_newsapi_news(symbol)
        if data and data.get('totalResults', 0) > 0:
            return {"source": "NewsAPI", "data": data}
        
        # Fallback to NewsData
        data = get_newsdata_news(symbol)
        if data and data.get('totalResults', 0) > 0:
            return {"source": "NewsData", "data": data}
            
        # Fallback to TheNewsAPI
        data = get_thenewsapi_news(symbol)
        if data and data.get('meta', {}).get('found', 0) > 0:
            return {"source": "TheNewsAPI", "data": data}
            
        return None

    @staticmethod
    def web_search(query: str) -> Optional[Dict[str, Any]]:
        # Primary search provider
        data = search_tavily(query)
        if data:
            return {"source": "Tavily", "data": data}
            
        return None

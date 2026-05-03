import os
import requests
from typing import Dict, Any, Optional

def get_fmp_data(endpoint: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from Financial Modeling Prep API."""
    api_key = os.getenv("FINANCIAL_MODELING_PREP_API_KEY")
    if not api_key:
        return None
    url = f"https://financialmodelingprep.com/api/v3/{endpoint}/{symbol}"
    params = {"apikey": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from FMP: {e}")
        return None

def get_finnhub_data(endpoint: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from Finnhub API."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    url = f"https://finnhub.io/api/v1/{endpoint}"
    params = {"symbol": symbol, "token": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from Finnhub: {e}")
        return None

def get_twelve_data(endpoint: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from Twelve Data API."""
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        return None
    url = f"https://api.twelvedata.com/{endpoint}"
    params = {"symbol": symbol, "apikey": api_key, **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from Twelve Data: {e}")
        return None

def get_eodhd_data(endpoint: str, symbol: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fetch data from EODHD API."""
    api_key = os.getenv("EODHD_API_KEY")
    if not api_key:
        return None
    url = f"https://eodhistoricaldata.com/api/{endpoint}/{symbol}"
    params = {"api_token": api_key, "fmt": "json", **kwargs}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from EODHD: {e}")
        return None

class FinancialKnowledgeBrain:
    """Aggregates multiple financial data vendors to provide income statement,
    cashflow, balance sheet, and stock data."""
    
    @staticmethod
    def get_income_statement(symbol: str) -> Optional[Dict[str, Any]]:
        # Try FMP first
        data = get_fmp_data("income-statement", symbol)
        if data: return {"source": "FMP", "data": data}
        
        # Fallback to EODHD
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Income_Statement")
        if data: return {"source": "EODHD", "data": data}
        
        return None

    @staticmethod
    def get_balance_sheet(symbol: str) -> Optional[Dict[str, Any]]:
        # Try FMP first
        data = get_fmp_data("balance-sheet-statement", symbol)
        if data: return {"source": "FMP", "data": data}
        
        # Fallback to EODHD
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Balance_Sheet")
        if data: return {"source": "EODHD", "data": data}
        
        return None

    @staticmethod
    def get_cashflow(symbol: str) -> Optional[Dict[str, Any]]:
        # Try FMP first
        data = get_fmp_data("cash-flow-statement", symbol)
        if data: return {"source": "FMP", "data": data}
        
        # Fallback to EODHD
        data = get_eodhd_data("fundamentals", symbol, filter="Financials::Cash_Flow")
        if data: return {"source": "EODHD", "data": data}
        
        return None

    @staticmethod
    def get_stock_data(symbol: str) -> Optional[Dict[str, Any]]:
        # Try Twelve Data
        data = get_twelve_data("quote", symbol)
        if data: return {"source": "TwelveData", "data": data}
        
        # Fallback to Finnhub
        data = get_finnhub_data("quote", symbol)
        if data: return {"source": "Finnhub", "data": data}
        
        return None

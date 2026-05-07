"""Citation ID generation helpers for IMPERIA evidence records."""

from __future__ import annotations

import hashlib

SOURCE_PREFIXES = {
    "sec": "c_edgar_",
    "sec edgar": "c_edgar_",
    "yfinance": "c_yf_",
    "yahoo finance": "c_yf_",
    "finnhub": "c_fh_",
    "newsapi": "c_news_",
    "newsdata": "c_news_",
    "thenewsapi": "c_news_",
    "polymarket": "c_poly_",
    "fred": "c_fred_",
    "form4": "c_insider_",
    "13f": "c_insider_",
    "earnings": "c_earn_",
    "computed": "c_calc_",
    "demo": "c_demo_",
}


def source_prefix(source: str) -> str:
    normalized = (source or "").lower().strip()
    return SOURCE_PREFIXES.get(normalized, "c_src_")


def stable_citation_id(source: str, *parts: object) -> str:
    digest = hashlib.sha1("|".join(str(part or "") for part in parts).encode("utf-8")).hexdigest()[:8]
    return f"{source_prefix(source)}{digest}"

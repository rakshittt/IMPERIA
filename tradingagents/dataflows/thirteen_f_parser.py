"""13F institutional-filing wrapper for IMPERIA expert research."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.dataflows import demo_provider
from tradingagents.dataflows.sec_edgar import get_13f_related_filings
from tradingagents.utils.validation import normalize_ticker


class ThirteenFFiling(BaseModel):
    filing_type: str | None = None
    filing_date: str | None = None
    accession_number: str | None = None
    url: str | None = None
    summary: str | None = None


class ThirteenFActivity(BaseModel):
    ticker: str
    filings: list[ThirteenFFiling] = Field(default_factory=list)
    limitation: str | None = None
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def get_thirteen_f_activity(ticker: str, limit: int = 50) -> ThirteenFActivity:
    """Return issuer-related 13F records with explicit lag/coverage warnings."""

    symbol = normalize_ticker(ticker)
    if demo_provider.is_demo_mode() and symbol in demo_provider.demo_universe():
        return ThirteenFActivity(
            ticker=symbol,
            filings=[
                ThirteenFFiling(
                    filing_type="13F-HR",
                    filing_date=datetime.now(timezone.utc).date().isoformat(),
                    accession_number=f"demo-13f-{symbol.lower()}",
                    url=f"https://example.com/imperia-demo/13f/{symbol.lower()}",
                    summary="Demo institutional activity sample.",
                )
            ],
            limitation="Demo 13F data is educational and not a live institutional ownership feed.",
            warnings=[demo_provider.DEMO_WARNING, "13F data is lagged by nature and may be stale."],
            citations=[demo_provider.demo_citation("13f", f"{symbol} demo 13F activity", ticker=symbol)],
        )
    try:
        payload = get_13f_related_filings(symbol, limit=limit)
    except Exception as exc:
        return ThirteenFActivity(
            ticker=symbol,
            warnings=[f"13F data unavailable ({type(exc).__name__}).", "13F data is lagged by nature and missing filing data reduces confidence."],
        )
    filings = [ThirteenFFiling.model_validate(row) for row in payload.get("filings", [])]
    citations = [
        {
            "id": f"c_insider_13f_{row.accession_number or index + 1}",
            "source_type": "institutional",
            "provider": "SEC EDGAR 13F",
            "title": f"{symbol} {row.filing_type or '13F'} filed {row.filing_date}",
            "url": row.url,
            "published_at": row.filing_date,
            "ticker": symbol,
        }
        for index, row in enumerate(filings)
    ]
    warnings = ["13F data is lagged by nature and should not be treated as current positioning."]
    if not filings:
        warnings.append(f"No issuer-related 13F-HR filings found for {symbol}.")
    return ThirteenFActivity(ticker=symbol, filings=filings, limitation=payload.get("limitation"), warnings=warnings, citations=citations)

"""Form 4 insider-activity wrapper for IMPERIA expert research."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from tradingagents.dataflows import demo_provider
from tradingagents.dataflows.sec_edgar import get_form4_insider_trades
from tradingagents.utils.validation import normalize_ticker


class Form4Transaction(BaseModel):
    filing_date: str | None = None
    insider_name: str | None = None
    transaction_code: str | None = None
    shares: float | None = None
    price: float | None = None
    acquired_disposed: str | None = None
    filing_url: str | None = None


class Form4Activity(BaseModel):
    ticker: str
    transactions: list[Form4Transaction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "", "None") else None
    except (TypeError, ValueError):
        return None


def get_form4_activity(ticker: str, limit: int = 50) -> Form4Activity:
    """Return parsed Form 4 activity or a structured no-data result."""

    symbol = normalize_ticker(ticker)
    if demo_provider.is_demo_mode() and symbol in demo_provider.demo_universe():
        return Form4Activity(
            ticker=symbol,
            transactions=[
                Form4Transaction(
                    filing_date=datetime.now(timezone.utc).date().isoformat(),
                    insider_name="Demo Officer",
                    transaction_code="A",
                    shares=1000,
                    price=100.0,
                    acquired_disposed="A",
                    filing_url=f"https://example.com/imperia-demo/form4/{symbol.lower()}",
                )
            ],
            warnings=[demo_provider.DEMO_WARNING, "Form 4 insider selling may be pre-planned under 10b5-1 plans."],
            citations=[demo_provider.demo_citation("form4", f"{symbol} demo Form 4 activity", ticker=symbol)],
        )
    try:
        filings = get_form4_insider_trades(symbol, limit=limit)
    except Exception as exc:
        return Form4Activity(
            ticker=symbol,
            warnings=[f"Form 4 data unavailable ({type(exc).__name__}).", "Missing Form 4 data reduces insider-activity confidence."],
        )

    transactions: list[Form4Transaction] = []
    citations: list[dict[str, Any]] = []
    for filing in filings:
        url = filing.get("url")
        filing_date = filing.get("filing_date")
        citations.append(
            {
                "id": f"c_insider_form4_{filing.get('accession_number') or len(citations) + 1}",
                "source_type": "insider",
                "provider": "SEC EDGAR Form 4",
                "title": f"{symbol} Form 4 filed {filing_date}",
                "url": url,
                "published_at": filing_date,
                "ticker": symbol,
            }
        )
        for tx in filing.get("transactions") or []:
            transactions.append(
                Form4Transaction(
                    filing_date=filing_date,
                    insider_name=filing.get("reporting_owner") or filing.get("owner_name"),
                    transaction_code=tx.get("transaction_code"),
                    shares=_float(tx.get("shares")),
                    price=_float(tx.get("price")),
                    acquired_disposed=tx.get("acquired_disposed"),
                    filing_url=url,
                )
            )
    warnings = ["Form 4 insider selling may be pre-planned under 10b5-1 plans."]
    if not filings:
        warnings.append(f"No recent Form 4 filings found for {symbol}.")
    if not transactions and filings:
        warnings.append("Form 4 filings were found, but no non-derivative transactions were parsed.")
    return Form4Activity(ticker=symbol, transactions=transactions, warnings=warnings, citations=citations)

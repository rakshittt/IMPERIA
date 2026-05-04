"""Free SEC EDGAR data access for US equities and major US ETFs."""

from __future__ import annotations

import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import requests

from tradingagents.cache.sqlite_cache import DEFAULT_TTLS, SQLiteCache, get_default_cache

logger = logging.getLogger(__name__)

SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUPPORTED_EXCHANGES = {"NASDAQ", "NYSE", "NYSE ARCA", "NYSE AMERICAN", "CBOE BZX"}
FOREIGN_ISSUER_HINTS = (
    " ADR",
    " ADS",
    " PLC",
    " S.A.",
    " S A ",
    " N.V.",
    " NV",
    " SE",
    " LTD",
    " LIMITED",
    " HOLDING LTD",
)
ETF_HINTS = (" ETF", " FUND", " TRUST", " SPDR", " ISHARES", " VANGUARD", " INVESCO")

_request_lock = Lock()
_last_request_at = 0.0


class SECError(RuntimeError):
    """Raised when SEC data cannot be fetched or normalized."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sec_user_agent() -> str:
    return os.getenv(
        "SEC_USER_AGENT",
        "TradingAgents/0.2.4 contact=dev@example.com",
    )


def _headers() -> dict[str, str]:
    return {
        "User-Agent": _sec_user_agent(),
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }


def _archive_headers() -> dict[str, str]:
    headers = _headers()
    headers["Host"] = "www.sec.gov"
    return headers


def _respect_rate_limit() -> None:
    global _last_request_at
    with _request_lock:
        min_interval = float(os.getenv("SEC_MIN_REQUEST_INTERVAL", "0.12"))
        elapsed = time.monotonic() - _last_request_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        _last_request_at = time.monotonic()


def _request_json(
    url: str,
    *,
    namespace: str,
    key: str,
    ttl_seconds: int | None = None,
    cache: SQLiteCache | None = None,
) -> dict[str, Any]:
    backend_cache = cache or get_default_cache()
    cached = backend_cache.get(namespace, key)
    if cached is not None:
        return cached

    timeout = float(os.getenv("SEC_REQUEST_TIMEOUT", "10"))
    retries = int(os.getenv("SEC_REQUEST_RETRIES", "3"))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            _respect_rate_limit()
            headers = _archive_headers() if "www.sec.gov" in url else _headers()
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise SECError(f"SEC returned HTTP {response.status_code} for {url}")
            response.raise_for_status()
            payload = response.json()
            backend_cache.set(
                namespace,
                key,
                payload,
                ttl_seconds=ttl_seconds or DEFAULT_TTLS.get(namespace, 3600),
                metadata={"url": url, "fetched_at": _now_iso()},
            )
            return payload
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))

    stale = backend_cache.get_stale(namespace, key)
    if stale is not None:
        logger.warning("Using stale SEC cache for %s:%s after %s", namespace, key, last_error)
        return stale
    raise SECError(f"SEC request failed for {url}: {last_error}") from last_error


def _request_text(url: str) -> str:
    timeout = float(os.getenv("SEC_REQUEST_TIMEOUT", "10"))
    retries = int(os.getenv("SEC_REQUEST_RETRIES", "2"))
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            _respect_rate_limit()
            response = requests.get(url, headers=_archive_headers(), timeout=timeout)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise SECError(f"SEC returned HTTP {response.status_code} for {url}")
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (2**attempt))
    raise SECError(f"SEC text request failed for {url}: {last_error}") from last_error


def _normalize_ticker(ticker: str) -> str:
    value = ticker.strip().upper().replace(".", "-")
    if not re.fullmatch(r"[A-Z0-9-]{1,10}", value):
        raise ValueError(f"Unsupported ticker format for SEC lookup: {ticker!r}")
    return value


def _is_supported_listing(entry: dict[str, Any]) -> bool:
    exchange = str(entry.get("exchange", "")).upper()
    title = str(entry.get("name", "")).upper()
    ticker = str(entry.get("ticker", "")).upper()
    if exchange not in SUPPORTED_EXCHANGES:
        return False
    if any(hint in title for hint in ETF_HINTS):
        return True
    if ticker in {"SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "IVV"}:
        return True
    return not any(hint in f" {title} " for hint in FOREIGN_ISSUER_HINTS)


def load_sec_ticker_universe(cache: SQLiteCache | None = None) -> list[dict[str, Any]]:
    """Load SEC ticker metadata filtered to supported US listings."""

    payload = _request_json(
        SEC_TICKERS_URL,
        namespace="search",
        key="sec_company_tickers_exchange",
        ttl_seconds=24 * 60 * 60,
        cache=cache,
    )
    fields = payload.get("fields", [])
    rows = payload.get("data", [])
    result: list[dict[str, Any]] = []
    for row in rows:
        raw = dict(zip(fields, row))
        entry = {
            "ticker": str(raw.get("ticker", "")).upper(),
            "name": raw.get("name") or raw.get("title") or "",
            "cik": int(raw.get("cik") or raw.get("cik_str") or 0),
            "exchange": raw.get("exchange") or "",
            "security_type": "ETF"
            if any(hint in str(raw.get("name", "")).upper() for hint in ETF_HINTS)
            else "Equity",
        }
        if entry["ticker"] and entry["cik"] and _is_supported_listing(entry):
            result.append(entry)
    return result


def get_cik_for_ticker(ticker: str) -> str:
    """Resolve a supported US ticker to a zero-padded 10-digit CIK."""

    symbol = _normalize_ticker(ticker)
    for entry in load_sec_ticker_universe():
        if entry["ticker"] == symbol:
            return f"{int(entry['cik']):010d}"
    raise ValueError(
        f"{ticker!r} is not a supported US-listed equity or major US ETF in SEC ticker data"
    )


def get_company_submissions(ticker: str) -> dict[str, Any]:
    cik = get_cik_for_ticker(ticker)
    return _request_json(
        f"{SEC_DATA_BASE}/submissions/CIK{cik}.json",
        namespace="sec_submissions",
        key=cik,
        ttl_seconds=DEFAULT_TTLS["sec_submissions"],
    )


def _filing_url(cik: str, accession_no: str, primary_document: str | None) -> str | None:
    if not accession_no or not primary_document:
        return None
    accession_path = accession_no.replace("-", "")
    return f"{SEC_ARCHIVES_BASE}/{int(cik)}/{accession_path}/{primary_document}"


def _normalize_recent_filings(submissions: dict[str, Any], cik: str) -> list[dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    if not recent:
        return []
    length = max((len(v) for v in recent.values() if isinstance(v, list)), default=0)
    filings: list[dict[str, Any]] = []
    for index in range(length):
        item = {}
        for field, values in recent.items():
            if isinstance(values, list) and index < len(values):
                item[field] = values[index]
        accession = item.get("accessionNumber")
        primary_document = item.get("primaryDocument")
        filings.append(
            {
                "ticker": submissions.get("tickers", [None])[0],
                "cik": cik,
                "accession_number": accession,
                "filing_type": item.get("form"),
                "filing_date": item.get("filingDate"),
                "report_date": item.get("reportDate"),
                "acceptance_datetime": item.get("acceptanceDateTime"),
                "primary_document": primary_document,
                "primary_doc_description": item.get("primaryDocDescription"),
                "url": _filing_url(cik, accession, primary_document),
                "source": "SEC EDGAR submissions",
            }
        )
    return filings


def get_sec_filings(
    ticker: str, filing_type: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    """Return recent SEC filings, optionally filtered by form type."""

    cik = get_cik_for_ticker(ticker)
    filings = _normalize_recent_filings(get_company_submissions(ticker), cik)
    if filing_type:
        target = filing_type.upper()
        filings = [
            filing
            for filing in filings
            if str(filing.get("filing_type", "")).upper() == target
            or str(filing.get("filing_type", "")).upper().startswith(f"{target}/")
        ]
    return filings[: max(0, limit)]


def get_companyfacts(ticker: str) -> dict[str, Any]:
    """Fetch raw SEC XBRL company facts for a supported ticker."""

    cik = get_cik_for_ticker(ticker)
    return _request_json(
        f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
        namespace="sec_companyfacts",
        key=cik,
        ttl_seconds=DEFAULT_TTLS["sec_companyfacts"],
    )


CONCEPTS: dict[str, list[str]] = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "assets": ["Assets"],
    "current_assets": ["AssetsCurrent"],
    "liabilities": ["Liabilities"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "debt": ["DebtCurrent", "LongTermDebtCurrent", "LongTermDebtNoncurrent"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}

UNIT_PREFS = ("USD", "USD/shares", "shares", "pure")


def _concept_units(facts: dict[str, Any], concept: str) -> dict[str, list[dict[str, Any]]]:
    return facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {})


def _latest_fact(
    facts: dict[str, Any], concepts: list[str], forms: set[str], annual: bool
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for concept in concepts:
        units = _concept_units(facts, concept)
        for unit in UNIT_PREFS:
            for fact in units.get(unit, []):
                form = str(fact.get("form", "")).upper()
                fp = str(fact.get("fp", "")).upper()
                if form not in forms:
                    continue
                if annual and fp != "FY":
                    continue
                if not annual and fp == "FY":
                    continue
                if "val" not in fact:
                    continue
                item = dict(fact)
                item["concept"] = concept
                item["unit"] = unit
                candidates.append(item)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.get("end") or "", item.get("filed") or ""), reverse=True)
    return candidates[0]


def _extract_statement(facts: dict[str, Any], annual: bool) -> dict[str, Any]:
    forms = {"10-K", "10-K/A"} if annual else {"10-Q", "10-Q/A"}
    statement: dict[str, Any] = {}
    for metric, concepts in CONCEPTS.items():
        if metric == "debt":
            debt_parts = []
            for concept in concepts:
                fact = _latest_fact(facts, [concept], forms, annual)
                if fact:
                    debt_parts.append(float(fact["val"]))
            if debt_parts:
                statement[metric] = {
                    "value": sum(debt_parts),
                    "unit": "USD",
                    "concept": "+".join(concepts),
                }
            continue
        fact = _latest_fact(facts, concepts, forms, annual)
        if fact:
            statement[metric] = {
                "value": fact.get("val"),
                "unit": fact.get("unit"),
                "fy": fact.get("fy"),
                "fp": fact.get("fp"),
                "end": fact.get("end"),
                "filed": fact.get("filed"),
                "form": fact.get("form"),
                "concept": fact.get("concept"),
            }
    return statement


def get_xbrl_financials(ticker: str) -> dict[str, Any]:
    """Return normalized SEC XBRL financial facts for annual and quarterly periods."""

    facts = get_companyfacts(ticker)
    cik = f"{int(facts.get('cik', get_cik_for_ticker(ticker))):010d}"
    return {
        "ticker": ticker.upper(),
        "cik": cik,
        "entity_name": facts.get("entityName"),
        "annual": _extract_statement(facts, annual=True),
        "quarterly": _extract_statement(facts, annual=False),
        "source": {
            "type": "SEC XBRL companyfacts",
            "url": f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{cik}.json",
            "fetched_at": _now_iso(),
        },
    }


def _parse_form4_transactions(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    transactions: list[dict[str, Any]] = []
    for node in root.findall(".//nonDerivativeTransaction"):
        def text(path: str) -> str | None:
            found = node.find(path)
            return found.text.strip() if found is not None and found.text else None

        transactions.append(
            {
                "security_title": text("./securityTitle/value"),
                "transaction_date": text("./transactionDate/value"),
                "transaction_code": text("./transactionCoding/transactionCode"),
                "shares": text("./transactionAmounts/transactionShares/value"),
                "price": text("./transactionAmounts/transactionPricePerShare/value"),
                "acquired_disposed": text("./transactionAmounts/transactionAcquiredDisposedCode/value"),
            }
        )
    return transactions


def get_form4_insider_trades(ticker: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return recent Form 4 filings with parsed transactions when XML is accessible."""

    filings = get_sec_filings(ticker, filing_type="4", limit=limit)
    enriched: list[dict[str, Any]] = []
    for filing in filings:
        item = dict(filing)
        transactions: list[dict[str, Any]] = []
        url = item.get("url")
        if url and str(url).lower().endswith((".xml", ".txt")):
            try:
                transactions = _parse_form4_transactions(_request_text(url))
            except Exception as exc:
                item["parse_warning"] = str(exc)
        item["transactions"] = transactions
        enriched.append(item)
    return enriched


def get_13f_related_filings(ticker: str, limit: int = 50) -> dict[str, Any]:
    """Return issuer-related 13F filings where available from free SEC data.

    Most operating companies do not file 13F-HR; investment managers do. This
    function exposes any direct 13F-HR filings for the resolved CIK and documents
    the free-data limitation instead of fabricating ownership aggregates.
    """

    filings = get_sec_filings(ticker, filing_type="13F-HR", limit=limit)
    return {
        "ticker": ticker.upper(),
        "filings": filings,
        "limitation": (
            "Free SEC issuer lookup only returns 13F-HR filings by the resolved CIK. "
            "Issuer-level institutional ownership aggregation requires parsing all "
            "manager 13F information tables and is not equivalent to paid ownership feeds."
        ),
    }


__all__ = [
    "SECError",
    "get_cik_for_ticker",
    "get_sec_filings",
    "get_companyfacts",
    "get_xbrl_financials",
    "get_form4_insider_trades",
    "get_13f_related_filings",
    "load_sec_ticker_universe",
]

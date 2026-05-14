import pytest

from tradingagents.providers.filings import edgar as sec_edgar


@pytest.mark.unit
def test_get_cik_for_ticker_filters_supported_universe(monkeypatch):
    monkeypatch.setattr(
        sec_edgar,
        "load_sec_ticker_universe",
        lambda: [
            {"ticker": "AAPL", "name": "Apple Inc.", "cik": 320193, "exchange": "NASDAQ"},
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF Trust", "cik": 884394, "exchange": "NYSE Arca"},
        ],
    )
    assert sec_edgar.get_cik_for_ticker("aapl") == "0000320193"
    assert sec_edgar.get_cik_for_ticker("SPY") == "0000884394"


@pytest.mark.unit
def test_get_cik_for_ticker_handles_dot_and_hyphen(monkeypatch):
    monkeypatch.setattr(
        sec_edgar,
        "load_sec_ticker_universe",
        lambda: [
            {"ticker": "BRK-B", "name": "Berkshire Hathaway Inc.", "cik": 1067983, "exchange": "NYSE"},
            {"ticker": "BF-B", "name": "Brown-Forman Corporation", "cik": 14693, "exchange": "NYSE"},
        ],
    )
    assert sec_edgar.get_cik_for_ticker("brk.b") == "0001067983"
    assert sec_edgar.get_cik_for_ticker("BF-B") == "0000014693"


@pytest.mark.unit
def test_get_sec_filings_filters_recent_forms(monkeypatch):
    monkeypatch.setattr(sec_edgar, "get_cik_for_ticker", lambda ticker: "0000320193")
    monkeypatch.setattr(
        sec_edgar,
        "get_company_submissions",
        lambda ticker: {
            "tickers": ["AAPL"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0001", "0002", "0003"],
                    "form": ["10-K", "10-Q", "4"],
                    "filingDate": ["2026-01-01", "2026-02-01", "2026-03-01"],
                    "reportDate": ["2025-12-31", "2026-01-31", "2026-03-01"],
                    "primaryDocument": ["a.htm", "q.htm", "f4.xml"],
                    "primaryDocDescription": ["10-K", "10-Q", "FORM 4"],
                    "acceptanceDateTime": ["", "", ""],
                }
            },
        },
    )
    filings = sec_edgar.get_sec_filings("AAPL", filing_type="10-K", limit=5)
    assert len(filings) == 1
    assert filings[0]["filing_type"] == "10-K"
    assert "sec.gov/Archives" in filings[0]["url"]


@pytest.mark.unit
def test_get_xbrl_financials_normalizes_companyfacts(monkeypatch):
    monkeypatch.setattr(sec_edgar, "get_cik_for_ticker", lambda ticker: "0000320193")
    monkeypatch.setattr(
        sec_edgar,
        "get_companyfacts",
        lambda ticker: {
            "cik": 320193,
            "entityName": "Apple Inc.",
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"form": "10-K", "fp": "FY", "fy": 2025, "end": "2025-09-30", "filed": "2025-10-30", "val": 100},
                                {"form": "10-Q", "fp": "Q1", "fy": 2026, "end": "2025-12-31", "filed": "2026-01-30", "val": 30},
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"form": "10-K", "fp": "FY", "fy": 2025, "end": "2025-09-30", "filed": "2025-10-30", "val": 20}
                            ]
                        }
                    },
                }
            },
        },
    )
    data = sec_edgar.get_xbrl_financials("AAPL")
    assert data["cik"] == "0000320193"
    assert data["annual"]["revenue"]["value"] == 100
    assert data["quarterly"]["revenue"]["value"] == 30


@pytest.mark.unit
def test_get_xbrl_financials_missing_tags(monkeypatch):
    monkeypatch.setattr(sec_edgar, "get_cik_for_ticker", lambda ticker: "0000320193")
    monkeypatch.setattr(
        sec_edgar,
        "get_companyfacts",
        lambda ticker: {"cik": 320193, "entityName": "Apple Inc.", "facts": {"us-gaap": {}}},
    )
    data = sec_edgar.get_xbrl_financials("AAPL")
    assert data["annual"] == {}
    assert data["quarterly"] == {}


@pytest.mark.unit
def test_form4_empty_xml_returns_empty_transactions(monkeypatch):
    monkeypatch.setattr(
        sec_edgar,
        "get_sec_filings",
        lambda ticker, filing_type=None, limit=50: [{"filing_type": "4", "url": "https://www.sec.gov/empty.xml"}],
    )
    monkeypatch.setattr(sec_edgar, "_request_text", lambda url: "")
    trades = sec_edgar.get_form4_insider_trades("AAPL")
    assert trades[0]["transactions"] == []


@pytest.mark.unit
def test_form4_and_13f_helpers(monkeypatch):
    monkeypatch.setattr(
        sec_edgar,
        "get_sec_filings",
        lambda ticker, filing_type=None, limit=50: [
            {
                "filing_type": filing_type,
                "url": "https://www.sec.gov/Archives/edgar/data/1/1/doc.xml",
            }
        ],
    )
    monkeypatch.setattr(
        sec_edgar,
        "_request_text",
        lambda url: """
        <ownershipDocument>
          <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-01-01</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
              <transactionShares><value>10</value></transactionShares>
              <transactionPricePerShare><value>1.23</value></transactionPricePerShare>
              <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
          </nonDerivativeTransaction>
        </ownershipDocument>
        """,
    )
    trades = sec_edgar.get_form4_insider_trades("AAPL", limit=1)
    assert trades[0]["transactions"][0]["transaction_code"] == "P"
    related = sec_edgar.get_13f_related_filings("AAPL", limit=1)
    assert related["filings"][0]["filing_type"] == "13F-HR"
    assert "limitation" in related

"""Manual live smoke test for the free US finance backend.

This script uses real free data providers and may take a little while. It is
not intended for CI.
"""

from __future__ import annotations

import time
import logging

from tradingagents.dataflows.market_data import get_market_indices, get_market_movers, get_quote
from tradingagents.dataflows.sec_edgar import get_cik_for_ticker
from tradingagents.dataflows.screener import parse_nl_screener_query, screen_stocks
from tradingagents.engine.fast_query import FastQueryEngine

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _check(name: str, func) -> None:
    start = time.perf_counter()
    try:
        result = func()
        elapsed = time.perf_counter() - start
        logger.info("%s %s (%.2fs)", "PASS" if result else "FAIL", name, elapsed)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.info("FAIL %s (%.2fs): %s", name, elapsed, exc)


def run() -> None:
    _check("quote AAPL", lambda: get_quote("AAPL").price is not None)
    _check("quote MSFT", lambda: get_quote("MSFT").price is not None)
    _check("market indices", lambda: len(get_market_indices()) >= 4)
    _check("top movers", lambda: bool(get_market_movers(3).gainers or get_market_movers(3).losers))
    _check("SEC CIK AAPL", lambda: get_cik_for_ticker("AAPL") == "0000320193")
    _check("fast query", lambda: bool(FastQueryEngine().answer_query("What is Apple's P/E?").get("answer")))
    _check("screener", lambda: screen_stocks(parse_nl_screener_query("profitable tech stocks")) is not None)


if __name__ == "__main__":
    run()

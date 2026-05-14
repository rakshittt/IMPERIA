"""Backward-compatible alias for the canonical ticker resolver."""

from __future__ import annotations

import sys

from tradingagents.core.query import ticker_resolver as _ticker_resolver

sys.modules[__name__] = _ticker_resolver

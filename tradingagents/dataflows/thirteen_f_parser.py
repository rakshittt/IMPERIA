"""Backward-compatible alias for the canonical 13F provider."""

from __future__ import annotations

import sys

from tradingagents.providers.filings import thirteen_f as _thirteen_f

sys.modules[__name__] = _thirteen_f

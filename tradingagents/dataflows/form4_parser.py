"""Backward-compatible alias for the canonical Form 4 provider."""

from __future__ import annotations

import sys

from tradingagents.providers.filings import form4 as _form4

sys.modules[__name__] = _form4

"""Backward-compatible alias for the canonical watchlist persistence module."""

from __future__ import annotations

import sys

from tradingagents.infra.db import watchlist as _watchlist

sys.modules[__name__] = _watchlist

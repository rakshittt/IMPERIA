"""Backward-compatible alias for the canonical expert-agent runtime."""

from __future__ import annotations

import sys

from tradingagents.core.research import runtime as _runtime

sys.modules[__name__] = _runtime

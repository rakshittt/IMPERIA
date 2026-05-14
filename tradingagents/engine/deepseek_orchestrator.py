"""Backward-compatible alias for the canonical DeepSeek orchestrator."""

from __future__ import annotations

import sys

from tradingagents.infra.llm import orchestrator as _orchestrator

sys.modules[__name__] = _orchestrator

"""Backward-compatible alias for the canonical DeepSeek helpers."""

from __future__ import annotations

import sys

from tradingagents.infra.llm import deepseek as _deepseek

sys.modules[__name__] = _deepseek

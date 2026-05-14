"""Backward-compatible alias for the canonical DeepSeek LangChain client."""

from __future__ import annotations

import sys

from tradingagents.infra.llm.clients import openai as _openai

sys.modules[__name__] = _openai

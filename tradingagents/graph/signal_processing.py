"""Backward-compatible adapter for older process_signal callers."""

from __future__ import annotations

from typing import Any


class SignalProcessor:
    """Return portfolio feedback text unchanged."""

    def __init__(self, quick_thinking_llm: Any = None):
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        return full_signal

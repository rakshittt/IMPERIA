"""Tests for the backward-compatible SignalProcessor adapter."""

from unittest.mock import MagicMock

import pytest

from tradingagents.graph.signal_processing import SignalProcessor


@pytest.mark.unit
class TestSignalProcessor:
    def test_returns_feedback_unchanged(self):
        feedback = "**Overall Assessment**: Portfolio feedback."
        assert SignalProcessor().process_signal(feedback) == feedback

    def test_makes_no_llm_calls(self):
        llm = MagicMock()
        sp = SignalProcessor(llm)
        sp.process_signal("Plain portfolio feedback.")
        llm.invoke.assert_not_called()
        llm.with_structured_output.assert_not_called()

"""Optional reflection helper for portfolio feedback logs."""

from typing import Any


class Reflector:
    """Creates concise lessons from explicit portfolio performance context."""

    def __init__(self, quick_thinking_llm: Any):
        self.quick_thinking_llm = quick_thinking_llm

    def reflect_on_portfolio_feedback(
        self,
        final_portfolio_feedback: str,
        performance_context: str,
    ) -> str:
        """Reflect only when external portfolio-performance context is supplied."""
        messages = [
            (
                "system",
                (
                    "You are reviewing prior portfolio research after the user "
                    "provided performance context. Write 2-4 concise sentences "
                    "with one concrete lesson for future portfolio analysis."
                ),
            ),
            (
                "human",
                (
                    f"Performance context:\n{performance_context}\n\n"
                    f"Prior portfolio feedback:\n{final_portfolio_feedback}"
                ),
            ),
        ]
        return self.quick_thinking_llm.invoke(messages).content

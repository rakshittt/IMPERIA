"""Append-only markdown memory log for portfolio research feedback."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import re


class TradingMemoryLog:
    """Append-only log of portfolio feedback and reusable research context."""

    _SEPARATOR = "\n\n<!-- ENTRY_END -->\n\n"
    _PORTFOLIO_RE = re.compile(r"PORTFOLIO:\n(.*?)(?=\nFEEDBACK:|\Z)", re.DOTALL)
    _FEEDBACK_RE = re.compile(r"FEEDBACK:\n(.*?)$", re.DOTALL)

    def __init__(self, config: dict = None):
        cfg = config or {}
        self._log_path = None
        path = cfg.get("memory_log_path")
        if path:
            self._log_path = Path(path).expanduser()
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._max_entries = cfg.get("memory_log_max_entries")

    def store_feedback(
        self,
        portfolio_key: str,
        analysis_date: str,
        portfolio_summary: str,
        final_portfolio_feedback: str,
    ) -> None:
        """Append a completed portfolio feedback entry."""
        if not self._log_path:
            return
        tag = f"[{analysis_date} | {portfolio_key}]"
        if self._log_path.exists():
            raw = self._log_path.read_text(encoding="utf-8")
            if any(line.strip() == tag for line in raw.splitlines()):
                return
        entry = (
            f"{tag}\n\n"
            f"PORTFOLIO:\n{portfolio_summary.strip()}\n\n"
            f"FEEDBACK:\n{final_portfolio_feedback.strip()}"
            f"{self._SEPARATOR}"
        )
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        self._rotate_file_if_needed()

    def store_decision(
        self,
        ticker: str,
        analysis_date: str,
        feedback_text: str,
    ) -> None:
        """Backward-compatible alias that stores a single-holding feedback entry."""
        self.store_feedback(
            portfolio_key=ticker,
            analysis_date=analysis_date,
            portfolio_summary=f"Single holding compatibility run: {ticker}",
            final_portfolio_feedback=feedback_text,
        )

    def load_entries(self) -> List[dict]:
        """Parse all portfolio feedback entries from the log."""
        if not self._log_path or not self._log_path.exists():
            return []
        text = self._log_path.read_text(encoding="utf-8")
        raw_entries = [e.strip() for e in text.split(self._SEPARATOR) if e.strip()]
        entries = []
        for raw in raw_entries:
            parsed = self._parse_entry(raw)
            if parsed:
                entries.append(parsed)
        return entries

    def get_pending_entries(self) -> List[dict]:
        """Portfolio feedback entries are stored as complete records."""
        return []

    def get_past_context(
        self, portfolio_key: str, n_same: int = 3, n_recent: int = 3
    ) -> str:
        """Return formatted prior portfolio feedback for prompt injection."""
        entries = self.load_entries()
        if not entries:
            return ""

        same, recent = [], []
        for entry in reversed(entries):
            if len(same) >= n_same and len(recent) >= n_recent:
                break
            if entry["portfolio_key"] == portfolio_key and len(same) < n_same:
                same.append(entry)
            elif entry["portfolio_key"] != portfolio_key and len(recent) < n_recent:
                recent.append(entry)

        if not same and not recent:
            return ""

        parts = []
        if same:
            parts.append("Past feedback for this portfolio (most recent first):")
            parts.extend(self._format_full(entry) for entry in same)
        if recent:
            parts.append("Recent portfolio research lessons from other portfolios:")
            parts.extend(self._format_summary(entry) for entry in recent)
        return "\n\n".join(parts)

    def update_with_outcome(self, *args, **kwargs) -> None:
        """Outcome tracking is intentionally unsupported for feedback entries."""
        return None

    def batch_update_with_outcomes(self, updates: List[dict]) -> None:
        """Outcome tracking is intentionally unsupported for feedback entries."""
        return None

    def _rotate_file_if_needed(self) -> None:
        if not self._log_path or not self._log_path.exists():
            return
        if not self._max_entries or self._max_entries <= 0:
            return
        blocks = self._log_path.read_text(encoding="utf-8").split(self._SEPARATOR)
        blocks = [block for block in blocks if block.strip()]
        if len(blocks) <= self._max_entries:
            return
        kept = blocks[-self._max_entries :]
        self._log_path.write_text(
            self._SEPARATOR.join(kept) + self._SEPARATOR,
            encoding="utf-8",
        )

    def _parse_entry(self, raw: str) -> Optional[dict]:
        lines = raw.strip().splitlines()
        if not lines:
            return None
        tag_line = lines[0].strip()
        if not (tag_line.startswith("[") and tag_line.endswith("]")):
            return None
        fields = [f.strip() for f in tag_line[1:-1].split("|")]
        if len(fields) != 2:
            return None
        body = "\n".join(lines[1:]).strip()
        portfolio_match = self._PORTFOLIO_RE.search(body)
        feedback_match = self._FEEDBACK_RE.search(body)
        return {
            "date": fields[0],
            "portfolio_key": fields[1],
            "portfolio": portfolio_match.group(1).strip() if portfolio_match else "",
            "feedback": feedback_match.group(1).strip() if feedback_match else "",
            "pending": False,
        }

    def _format_full(self, entry: dict) -> str:
        tag = f"[{entry['date']} | {entry['portfolio_key']}]"
        return "\n\n".join(
            [
                tag,
                f"PORTFOLIO:\n{entry['portfolio']}",
                f"FEEDBACK:\n{entry['feedback']}",
            ]
        )

    def _format_summary(self, entry: dict) -> str:
        tag = f"[{entry['date']} | {entry['portfolio_key']}]"
        text = entry["feedback"][:500]
        suffix = "..." if len(entry["feedback"]) > 500 else ""
        return f"{tag}\n{text}{suffix}"

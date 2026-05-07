"""Structured citation models for IMPERIA evidence bundles and agent outputs."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def citation_fingerprint(source: str, url: str | None = None, published_at: str | datetime | None = None, title: str | None = None) -> str:
    """Create a stable fingerprint for deduplicating source records."""

    raw = "|".join(str(part or "").strip().lower() for part in (source, url, published_at, title))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Citation(BaseModel):
    """Grounding metadata attached to every data point that can feed an agent."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str
    source: str
    url: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    snippet: str | None = None
    fingerprint: str
    ticker: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        *,
        citation_id: str,
        source: str,
        url: str | None = None,
        title: str | None = None,
        published_at: str | datetime | None = None,
        snippet: str | None = None,
        ticker: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Citation":
        parsed_published_at: datetime | None = None
        if isinstance(published_at, datetime):
            parsed_published_at = published_at
        elif isinstance(published_at, str) and published_at:
            try:
                parsed_published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                parsed_published_at = None
        return cls(
            citation_id=citation_id,
            source=source,
            url=url,
            title=title,
            published_at=parsed_published_at,
            snippet=snippet,
            ticker=ticker,
            fingerprint=citation_fingerprint(source, url, parsed_published_at or published_at, title),
            metadata=metadata or {},
        )

    def api_dict(self) -> dict[str, Any]:
        """Return the existing API citation shape while preserving the canonical ID."""

        return {
            "id": self.citation_id,
            "citation_id": self.citation_id,
            "source_type": self.metadata.get("source_type") or self.source,
            "provider": self.source,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "accessed_at": self.retrieved_at.isoformat(),
            "ticker": self.ticker,
            "confidence": self.metadata.get("confidence"),
            "relevance_score": self.metadata.get("relevance_score"),
            "metadata": self.metadata,
        }

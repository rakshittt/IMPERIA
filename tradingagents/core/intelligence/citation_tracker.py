"""Structured source citation tracking for fast financial answers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Citation:
    source_type: str
    id: str | None = None
    provider: str | None = None
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    published_at: str | None = None
    timestamp: str = field(default_factory=utc_now_iso)
    accessed_at: str = field(default_factory=utc_now_iso)
    ticker: str | None = None
    confidence: float | None = None
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def dedupe_key(self) -> tuple[str, str, str]:
        return (
            self.source_type.strip().lower(),
            (self.url or "").strip().lower(),
            (self.title or "").strip().lower(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CitationTracker:
    """Collects citations and deduplicates them by source/url/title."""

    def __init__(self) -> None:
        self._items: list[Citation] = []
        self._seen: set[tuple[str, str, str]] = set()

    def add(
        self,
        source_type: str,
        *,
        provider: str | None = None,
        title: str | None = None,
        url: str | None = None,
        snippet: str | None = None,
        published_at: str | None = None,
        timestamp: str | None = None,
        accessed_at: str | None = None,
        ticker: str | None = None,
        confidence: float | None = None,
        relevance_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Citation:
        citation = Citation(
            id=f"cit-{len(self._items) + 1}",
            source_type=source_type,
            provider=provider,
            title=title,
            url=url,
            snippet=snippet,
            published_at=published_at,
            timestamp=timestamp or utc_now_iso(),
            accessed_at=accessed_at or utc_now_iso(),
            ticker=ticker,
            confidence=confidence,
            relevance_score=relevance_score,
            metadata=metadata or {},
        )
        key = citation.dedupe_key()
        if key not in self._seen:
            self._seen.add(key)
            self._items.append(citation)
        return citation

    def extend(self, citations: list[Citation | dict[str, Any]]) -> None:
        for citation in citations:
            if isinstance(citation, Citation):
                self.add(
                    citation.source_type,
                    provider=citation.provider,
                    title=citation.title,
                    url=citation.url,
                    snippet=citation.snippet,
                    published_at=citation.published_at,
                    timestamp=citation.timestamp,
                    accessed_at=citation.accessed_at,
                    ticker=citation.ticker,
                    confidence=citation.confidence,
                    relevance_score=citation.relevance_score,
                    metadata=citation.metadata,
                )
            else:
                self.add(
                    str(citation.get("source_type", "unknown")),
                    provider=citation.get("provider"),
                    title=citation.get("title"),
                    url=citation.get("url"),
                    snippet=citation.get("snippet"),
                    published_at=citation.get("published_at"),
                    timestamp=citation.get("timestamp"),
                    accessed_at=citation.get("accessed_at"),
                    ticker=citation.get("ticker"),
                    confidence=citation.get("confidence"),
                    relevance_score=citation.get("relevance_score"),
                    metadata=citation.get("metadata") or {},
                )

    def as_list(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._items]

    def __len__(self) -> int:
        return len(self._items)


def attach_citations(
    response: dict[str, Any], citations: CitationTracker | list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach structured citations to a response object."""

    response["citations"] = citations.as_list() if isinstance(citations, CitationTracker) else citations
    response["citation_count"] = len(response["citations"])
    response["citations_available"] = bool(response["citations"])
    return response

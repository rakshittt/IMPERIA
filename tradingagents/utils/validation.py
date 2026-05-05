"""Input validation helpers for the free US finance backend."""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator

TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,6}$")


def normalize_ticker(ticker: str) -> str:
    """Return a normalized US-style ticker or raise ``ValueError``."""

    symbol = ticker.strip().upper().replace(".", "-")
    if not symbol:
        raise ValueError("Ticker is required.")
    if len(symbol) > 6:
        raise ValueError("Ticker must be 6 characters or fewer.")
    if not TICKER_PATTERN.fullmatch(symbol):
        raise ValueError("Ticker must contain only A-Z, 0-9, dot, or hyphen.")
    if " " in ticker or symbol.isdigit():
        raise ValueError("Ticker must be a US equity or major US ETF symbol.")
    return symbol


def validate_iso_date(value: str | None) -> str | None:
    """Validate an ISO 8601 date string and return it unchanged."""

    if value in (None, ""):
        return None
    try:
        date.fromisoformat(value)
    except Exception as exc:
        raise ValueError("Date must be ISO 8601 format YYYY-MM-DD.") from exc
    return value


class TickerPath(BaseModel):
    """Reusable request model for ticker path validation."""

    ticker: str = Field(..., min_length=1, max_length=12)

    @field_validator("ticker")
    @classmethod
    def valid_ticker(cls, value: str) -> str:
        return normalize_ticker(value)


class DateRange(BaseModel):
    """Reusable ISO date range validator."""

    start: str | None = None
    end: str | None = None

    @field_validator("start", "end")
    @classmethod
    def valid_date(cls, value: str | None) -> str | None:
        return validate_iso_date(value)

    @model_validator(mode="after")
    def valid_range(self) -> "DateRange":
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be on or before end.")
        return self

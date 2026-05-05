"""Pydantic request and response contracts for the backend API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from tradingagents.utils.validation import normalize_ticker, validate_iso_date


class PortfolioHolding(BaseModel):
    ticker: str
    weight: float | None = None
    shares: float | None = None
    cost_basis: float | None = None

    @field_validator("ticker")
    @classmethod
    def ticker_is_supported(cls, value: str) -> str:
        return normalize_ticker(value)

    @field_validator("weight")
    @classmethod
    def weight_is_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("weight must be non-negative.")
        return value


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    portfolio: list[PortfolioHolding] | None = None
    date: str | None = None
    profile: dict[str, Any] | None = None

    @field_validator("date")
    @classmethod
    def date_is_iso(cls, value: str | None) -> str | None:
        return validate_iso_date(value)


class ResearchRequest(BaseModel):
    portfolio: list[PortfolioHolding]
    date: str | None = None
    profile: dict[str, Any] | None = None

    @field_validator("date")
    @classmethod
    def research_date_is_iso(cls, value: str | None) -> str | None:
        return validate_iso_date(value)


class WatchlistCreateRequest(BaseModel):
    name: str
    tickers: list[str] = Field(default_factory=list)

    @field_validator("tickers")
    @classmethod
    def tickers_are_supported(cls, value: list[str]) -> list[str]:
        return [normalize_ticker(ticker) for ticker in value]


class WatchlistTickerRequest(BaseModel):
    ticker: str

    @field_validator("ticker")
    @classmethod
    def watchlist_ticker_is_supported(cls, value: str) -> str:
        return normalize_ticker(value)


class ScreenerNLRequest(BaseModel):
    query: str = Field(..., min_length=1)


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class FastAnswerResponse(BaseModel):
    mode: str
    answer: str
    key_stats: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: str | None = None

"""Pydantic request and response contracts for the backend API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PortfolioHolding(BaseModel):
    ticker: str
    weight: float | None = None
    shares: float | None = None
    cost_basis: float | None = None


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1)
    portfolio: list[PortfolioHolding] | None = None
    date: str | None = None
    profile: dict[str, Any] | None = None


class ResearchRequest(BaseModel):
    portfolio: list[PortfolioHolding]
    date: str | None = None
    profile: dict[str, Any] | None = None


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

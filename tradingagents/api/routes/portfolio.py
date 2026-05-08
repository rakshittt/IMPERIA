"""Portfolio snapshot APIs.

Portfolio snapshots are a persistence module for research organization. They
are not required inputs for stock-first fast queries or deep research.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from tradingagents.api.responses import standard_response
from tradingagents.persistence.portfolio import delete_portfolio_snapshot, get_portfolio_snapshot, list_portfolio_snapshots, save_portfolio_snapshot
from tradingagents.utils.validation import normalize_ticker

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class PortfolioSnapshotRequest(BaseModel):
    label: str = "Research snapshot"
    holdings: dict[str, float] = Field(default_factory=dict)
    research_id: str | None = None

    @field_validator("holdings")
    @classmethod
    def holdings_are_supported(cls, value: dict[str, float]) -> dict[str, float]:
        result: dict[str, float] = {}
        for ticker, weight in value.items():
            if weight < 0:
                raise ValueError("portfolio snapshot weights must be non-negative")
            result[normalize_ticker(ticker)] = float(weight)
        return result


@router.post("/snapshots")
async def create_snapshot(payload: PortfolioSnapshotRequest):
    record = save_portfolio_snapshot(payload.holdings, payload.label)
    data: dict[str, Any] = record.model_dump()
    if payload.research_id:
        data["research_id"] = payload.research_id
    return standard_response(data, mode="fast", intent="portfolio_snapshot", data_quality="good")


@router.get("/snapshots")
async def list_snapshots():
    return standard_response({"snapshots": [item.model_dump() for item in list_portfolio_snapshots()]}, mode="fast", intent="portfolio_snapshot", data_quality="good")


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    try:
        record = get_portfolio_snapshot(snapshot_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Portfolio snapshot not found.")
    return standard_response(record.model_dump(), mode="fast", intent="portfolio_snapshot", data_quality="good")


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    try:
        delete_portfolio_snapshot(snapshot_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Portfolio snapshot not found.")
    return standard_response({"deleted": True, "id": snapshot_id}, mode="fast", intent="portfolio_snapshot", data_quality="good")

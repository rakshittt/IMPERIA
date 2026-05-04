from __future__ import annotations

from fastapi import APIRouter, Query

from tradingagents.api.deps import get_fast_engine
from tradingagents.api.models import SearchResponse

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=25)):
    engine = get_fast_engine()
    return {"query": q, "results": engine.search(q, limit=limit)}

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from tradingagents.api.deps import get_fast_engine
from tradingagents.api.models import AskRequest, ResearchRequest
from tradingagents.api.responses import standard_response
from tradingagents.api.services import run_deep_research, run_stock_expert_research
from tradingagents.engine.query_router import route_query
from tradingagents.engine.safety import assess_query, reframe_prompt, sanitize_answer
from tradingagents.engine import stock_intelligence
from tradingagents.expert_agents.planner import plan_query
from tradingagents.expert_agents.runtime import ExpertAgentRuntime
from tradingagents.workers.background_jobs import submit_research_job

router = APIRouter(prefix="/api", tags=["ai"])


def _holdings_from_tickers(tickers: list[str]) -> list[dict[str, Any]]:
    if not tickers:
        return []
    weight = 1.0 / len(tickers)
    return [{"ticker": ticker, "weight": weight} for ticker in tickers]


def _hybrid_fast_response(payload: dict[str, Any], *, intent: str, ticker: str | None = None) -> dict[str, Any]:
    data = dict(payload)
    if ticker:
        data.setdefault("ticker", ticker)
    answer = sanitize_answer(str(data.get("answer") or "I could not synthesize an answer from the available data."))
    data["answer"] = answer
    response = standard_response(
        data,
        citations=data.get("citations", []),
        warnings=data.get("warnings", []),
        mode="fast",
        intent=intent,
        providers_used=data.get("providers_used") or data.get("metadata", {}).get("providers_used", []),
        data_quality="partial" if data.get("warnings") else "good",
    )
    response.update(
        {
            "mode": "fast",
            "answer": answer,
            "ticker": data.get("ticker"),
            "citations_available": response["metadata"]["citations_available"],
            "citation_count": response["metadata"]["citation_count"],
        }
    )
    return response


def _expert_fast_response(query: str, ticker: str, *, window: str | None = None) -> dict[str, Any]:
    runtime = ExpertAgentRuntime()
    result = runtime.run(query=query, ticker=ticker, mode="fast", window=window)
    report = result.final_report
    answer = sanitize_answer(str(report.get("executive_summary") or report.get("summary") or "IMPERIA could not synthesize a fast expert answer from available evidence."))
    data = {
        "answer": answer,
        "mode": "fast",
        "ticker": result.ticker,
        "intent": result.intent,
        "time_window": result.time_window,
        "data_used": {
            "contributing_agents": report.get("contributing_agents", []),
            "agent_count": len(result.agent_outputs),
        },
        "final_report": report,
        "agent_outputs": result.agent_outputs,
        "not_investment_advice": True,
    }
    response = standard_response(
        data,
        citations=result.citations,
        warnings=result.warnings,
        mode="fast",
        intent=result.intent,
        providers_used=result.providers_used,
        data_quality=result.data_quality,
    )
    response.update({"mode": "fast", "answer": answer, "ticker": result.ticker})
    return response


@router.post("/ask")
async def ask(payload: AskRequest):
    query = f"{payload.query} {payload.ticker}" if payload.ticker and payload.ticker not in payload.query.upper() else payload.query
    route = route_query(query)
    ticker = payload.ticker or (route.tickers[0] if route.tickers else None)
    safety = assess_query(payload.query)
    if safety.requires_reframe:
        snapshot = stock_intelligence.build_research_snapshot(ticker) if ticker else {}
        answer = reframe_prompt(ticker)
        data = {
            "answer": answer,
            "mode": "fast",
            "ticker": ticker,
            "intent": "safety_reframe",
            "research_factors": snapshot,
            "not_investment_advice": True,
        }
        return _hybrid_fast_response(data, intent="safety_reframe", ticker=ticker)

    if route.mode == "fast":
        expert_plan = plan_query(payload.query, selected_ticker=ticker, window=payload.window, explicit_mode="fast")
        if ticker and expert_plan.intent not in {"simple_lookup", "out_of_scope"}:
            return _expert_fast_response(payload.query, ticker, window=payload.window)
        if ticker and any(term in payload.query.lower() for term in ("what happened", "why", "moving", "moved")):
            return _hybrid_fast_response(stock_intelligence.build_what_happened(ticker, window=payload.window or "today"), intent="what_happened", ticker=ticker)
        if ticker and "sentiment" in payload.query.lower():
            sentiment = stock_intelligence.get_stock_sentiment(ticker, window=payload.window or "today").model_dump()
            sentiment["answer"] = sentiment.get("summary")
            return _hybrid_fast_response(sentiment, intent="sentiment", ticker=ticker)
        if ticker and "risk" in payload.query.lower():
            risks = stock_intelligence.build_risks(ticker)
            risks["answer"] = f"{ticker} risks to research include: " + "; ".join(risks.get("risks", [])[:4])
            return _hybrid_fast_response(risks, intent="risks", ticker=ticker)
        answer_payload = get_fast_engine().answer_query(query)
        return _hybrid_fast_response(answer_payload, intent=route.intent, ticker=ticker)

    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio or []]
    if not portfolio:
        portfolio = _holdings_from_tickers([ticker] if ticker else route.tickers)
    if not portfolio:
        return JSONResponse(
            standard_response(
                {"mode": "deep", "route": route.to_dict()},
                warnings=["Deep research requires at least one supported US equity or ETF ticker."],
                mode="deep",
                intent=route.intent,
                data_quality="poor",
            ),
            status_code=400,
        )
    profile = payload.profile or {}
    profile.update({"question": payload.query, "window": payload.window, "focus": payload.focus, "stock_first": bool(ticker)})
    runner = run_stock_expert_research if ticker and not payload.portfolio else run_deep_research
    submitted = submit_research_job(runner, portfolio, payload.date, profile)
    response = standard_response(
        {"mode": "deep", "route": route.to_dict(), "research_id": submitted["research_id"], "status": submitted["status"], "ticker": ticker},
        warnings=[],
        mode="deep",
        intent=route.intent,
        data_quality="partial",
    )
    response.update({"mode": "deep", "research_id": submitted["research_id"], "status": submitted["status"]})
    return response


@router.post("/analyze")
async def analyze_compat(request: Request):
    data = await request.json()
    payload = ResearchRequest(
        portfolio=data.get("portfolio", []),
        ticker=data.get("ticker"),
        question=data.get("question"),
        window=data.get("window"),
        focus=data.get("focus"),
        date=data.get("date") or datetime.now().strftime("%Y-%m-%d"),
        profile=data.get("profile", {}),
    )
    portfolio = [item.model_dump(exclude_none=True) for item in payload.portfolio or []]
    if not portfolio and payload.ticker:
        portfolio = [{"ticker": payload.ticker, "weight": 1.0}]
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_deep_research, portfolio, payload.date, payload.profile or {})

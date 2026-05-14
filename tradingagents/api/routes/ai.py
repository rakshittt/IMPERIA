from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from tradingagents.api.deps import get_fast_engine
from tradingagents.api.models import AskRequest, ResearchRequest
from tradingagents.api.responses import standard_response
from tradingagents.api.services import run_stock_expert_research
from tradingagents.core.query.router import route_query
from tradingagents.core.safety import assess_query, reframe_prompt, sanitize_answer
from tradingagents.core.intelligence import stock as stock_intelligence
import tradingagents.providers.market.data as market_data
from tradingagents.core.agents.planner import plan_query
from tradingagents.core.research.runtime import ExpertAgentRuntime
from tradingagents.infra.llm.deepseek import deepseek_text
from tradingagents.utils.validation import normalize_ticker
from tradingagents.core.research.jobs import submit_research_job

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


def _extract_json_block(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _run_selected_api(api_name: str, args: dict[str, Any], *, fallback_ticker: str, fallback_window: str) -> dict[str, Any]:
    engine = get_fast_engine()
    ticker = normalize_ticker(str(args.get("ticker") or fallback_ticker))
    window = str(args.get("window") or fallback_window)
    limit = int(args.get("limit") or 10)

    if api_name == "stock_summary":
        return stock_intelligence.build_research_snapshot(ticker, window=window)
    if api_name == "stock_what_happened":
        return stock_intelligence.build_what_happened(ticker, window=window)
    if api_name == "stock_sentiment":
        return stock_intelligence.get_stock_sentiment(ticker, window=window).model_dump()
    if api_name == "stock_risks":
        return stock_intelligence.build_risks(ticker)
    if api_name == "stock_news":
        return {"ticker": ticker, "window": window, "news": engine.get_news(ticker, limit=limit)}
    if api_name == "stock_ratios":
        return engine.get_ratios(ticker)
    if api_name == "market_summary":
        return {
            "indices": [item.model_dump() for item in market_data.get_market_indices()],
            "movers": market_data.get_market_movers(n=5).model_dump(),
            "breadth": market_data.get_market_breadth().model_dump(),
        }
    if api_name == "compare":
        left = normalize_ticker(str(args.get("ticker_a") or "AMD"))
        right = normalize_ticker(str(args.get("ticker_b") or "NVDA"))
        return stock_intelligence.compare_stocks(left, right)
    if api_name == "earnings_brief":
        return stock_intelligence.build_earnings_brief(ticker)
    if api_name == "filing_brief":
        return stock_intelligence.build_filing_brief(ticker)
    if api_name == "investor_checklist":
        return stock_intelligence.build_investor_checklist(ticker)

    return {"error": f"Unsupported api_name: {api_name}"}


@router.post("/agent/analyst")
async def analyst_agent(request: Request):
    payload = await request.json()
    query = str(payload.get("query") or "").strip()
    if not query:
        return JSONResponse({"error": "query is required"}, status_code=422)
    ticker = normalize_ticker(str(payload.get("ticker") or "AAPL"))
    window = str(payload.get("window") or "today")

    tool_catalog = [
        "stock_summary",
        "stock_what_happened",
        "stock_sentiment",
        "stock_risks",
        "stock_news",
        "stock_ratios",
        "market_summary",
        "compare",
        "earnings_brief",
        "filing_brief",
        "investor_checklist",
    ]

    planner_prompt = (
        "You are a routing planner for a stock research backend.\n"
        f"User query: {query}\n"
        f"Default ticker: {ticker}\n"
        f"Default window: {window}\n"
        f"Available tools: {', '.join(tool_catalog)}.\n"
        "Return strict JSON only with this schema:\n"
        '{"apis":[{"api_name":"stock_summary","args":{"ticker":"AAPL","window":"today"}}],"reason":"short reason"}\n'
        "Pick 1-4 tools max."
    )
    planned_text = deepseek_text([{"role": "user", "content": planner_prompt}], mode="fast", temperature=0.1)
    plan = _extract_json_block(planned_text or "")
    selected = plan.get("apis") if isinstance(plan.get("apis"), list) else []
    if not selected:
        selected = [{"api_name": "stock_summary", "args": {"ticker": ticker, "window": window}}]

    executed: list[dict[str, Any]] = []
    for item in selected[:4]:
        api_name = str(item.get("api_name") or "").strip()
        args = item.get("args") if isinstance(item.get("args"), dict) else {}
        if not api_name:
            continue
        try:
            result = _run_selected_api(api_name, args, fallback_ticker=ticker, fallback_window=window)
            executed.append({"api_name": api_name, "args": args, "result": result})
        except Exception as exc:
            executed.append({"api_name": api_name, "args": args, "error": f"{type(exc).__name__}: {exc}"})

    formatter_prompt = (
        "You are a Wall Street equity research analyst.\n"
        "Write a concise natural-language response with:\n"
        "1) Thesis\n2) What data says\n3) Risks\n4) What to watch next.\n"
        "Do not provide investment advice. Keep it factual and source-grounded.\n\n"
        f"User query: {query}\n"
        f"API execution results JSON:\n{json.dumps(executed, default=str)}"
    )
    analyst_text = deepseek_text([{"role": "user", "content": formatter_prompt}], mode="deep", temperature=0.2)
    if not analyst_text:
        analyst_text = "I could not generate an analyst-style narrative right now. Please retry."

    return {
        "query": query,
        "ticker": ticker,
        "window": window,
        "plan": {"reason": plan.get("reason"), "apis": selected},
        "api_runs": executed,
        "analyst_response": sanitize_answer(analyst_text),
    }


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
    submitted = submit_research_job(run_stock_expert_research, portfolio, payload.date, profile)
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
    """Backward-compatible synchronous research endpoint.

    Submits a background job and returns the job handle immediately.
    Clients should poll /api/research/{id} or use the SSE stream.
    """
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
    profile = payload.profile or {}
    profile.setdefault("ticker", payload.ticker or (portfolio[0].get("ticker") if portfolio else None))
    profile.setdefault("question", payload.question)
    profile.setdefault("window", payload.window)
    return submit_research_job(run_stock_expert_research, portfolio, payload.date, profile)

import os
import json
import asyncio
import uuid
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from dotenv import load_dotenv

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.utils import portfolio_key
from tradingagents.agents.utils.agent_utils import build_portfolio_context

load_dotenv()

app = FastAPI(title="TradingAgents Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve legacy frontend
if os.path.isdir("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Setup config
config = DEFAULT_CONFIG.copy()
config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gpt-4o-mini")
config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")

ta = TradingAgentsGraph(debug=True, config=config)

# In-memory research store
research_store = {}


# ─── Quote endpoint ───────────────────────────────────────────────
@app.get("/api/quote/{ticker}")
async def get_quote(ticker: str):
    """Fetch real-time quote for a US ticker using yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.fast_info
        hist = t.history(period="2d")

        prev_close = float(info.previous_close) if hasattr(info, 'previous_close') else None
        last_price = float(info.last_price) if hasattr(info, 'last_price') else None

        if last_price and prev_close:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100
        else:
            change = 0
            change_pct = 0

        # Get fuller info for fundamentals
        full_info = t.info

        return {
            "ticker": ticker.upper(),
            "name": full_info.get("shortName", ticker.upper()),
            "exchange": full_info.get("exchange", ""),
            "sector": full_info.get("sector", ""),
            "industry": full_info.get("industry", ""),
            "price": last_price,
            "change": round(change, 2),
            "changePct": round(change_pct, 2),
            "prevClose": prev_close,
            "open": full_info.get("open"),
            "dayHigh": full_info.get("dayHigh"),
            "dayLow": full_info.get("dayLow"),
            "volume": full_info.get("volume"),
            "avgVolume": full_info.get("averageVolume"),
            "marketCap": full_info.get("marketCap"),
            "pe": full_info.get("trailingPE"),
            "forwardPe": full_info.get("forwardPE"),
            "eps": full_info.get("trailingEps"),
            "dividend": full_info.get("dividendYield"),
            "beta": full_info.get("beta"),
            "fiftyTwoWeekHigh": full_info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": full_info.get("fiftyTwoWeekLow"),
            "avgAnalystRating": full_info.get("recommendationKey"),
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── Trending endpoint ────────────────────────────────────────────
@app.get("/api/trending")
async def get_trending():
    """Return top US movers — uses a curated list with live quotes."""
    import yfinance as yf

    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "AMD", "NFLX", "JPM"]
    results = []
    try:
        data = yf.download(tickers, period="2d", group_by="ticker", progress=False)
        for sym in tickers:
            try:
                if len(tickers) > 1:
                    df = data[sym] if sym in data.columns.get_level_values(0) else None
                else:
                    df = data
                if df is None or df.empty:
                    continue
                last = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-2]) if len(df) > 1 else last
                chg = last - prev
                chg_pct = (chg / prev * 100) if prev else 0
                results.append({
                    "ticker": sym,
                    "price": round(last, 2),
                    "change": round(chg, 2),
                    "changePct": round(chg_pct, 2),
                })
            except Exception:
                continue
    except Exception:
        # Fallback: return static list
        for sym in tickers:
            results.append({"ticker": sym, "price": 0, "change": 0, "changePct": 0})

    return results


# ─── Market snapshot ───────────────────────────────────────────────
@app.get("/api/market-snapshot")
async def market_snapshot():
    """Return major US index summary."""
    import yfinance as yf

    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
    }
    results = []
    for name, sym in indices.items():
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = float(info.last_price)
            prev = float(info.previous_close)
            chg = price - prev
            chg_pct = (chg / prev * 100) if prev else 0
            results.append({
                "name": name,
                "symbol": sym,
                "price": round(price, 2),
                "change": round(chg, 2),
                "changePct": round(chg_pct, 2),
            })
        except Exception:
            results.append({"name": name, "symbol": sym, "price": 0, "change": 0, "changePct": 0})
    return results


# ─── Full analysis ─────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze(request: Request):
    data = await request.json()
    portfolio = data.get("portfolio", [])
    analysis_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    user_profile = data.get("profile", {})

    try:
        loop = asyncio.get_event_loop()
        final_state, feedback = await loop.run_in_executor(
            None, ta.analyze_portfolio, portfolio, analysis_date, user_profile
        )

        rid = str(uuid.uuid4())[:8]
        result = {
            "id": rid,
            "market_report": final_state.get("market_report"),
            "sentiment_report": final_state.get("sentiment_report"),
            "news_report": final_state.get("news_report"),
            "fundamentals_report": final_state.get("fundamentals_report"),
            "macro_report": final_state.get("macro_report"),
            "bullish_research": final_state.get("bullish_research"),
            "bearish_research": final_state.get("bearish_research"),
            "research_synthesis": final_state.get("research_synthesis"),
            "trader_report": final_state.get("trader_report"),
            "risk_report": final_state.get("risk_report"),
            "final_portfolio_feedback": final_state.get("final_portfolio_feedback"),
        }
        research_store[rid] = result
        return JSONResponse(result)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── Retrieve saved research ──────────────────────────────────────
@app.get("/api/research/{rid}")
async def get_research(rid: str):
    if rid in research_store:
        return research_store[rid]
    return JSONResponse({"error": "Research not found"}, status_code=404)


# ─── SSE streaming research ───────────────────────────────────────
@app.post("/api/research/stream")
async def stream_research(request: Request):
    data = await request.json()
    portfolio = data.get("portfolio", [])
    analysis_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    user_profile = data.get("profile", {})

    async def event_generator():
        loop = asyncio.get_event_loop()
        stages = [
            "market_report", "sentiment_report", "news_report",
            "fundamentals_report", "macro_report", "bullish_research",
            "bearish_research", "research_synthesis", "trader_report",
            "risk_report", "final_portfolio_feedback"
        ]
        # Run the full pipeline
        try:
            final_state, feedback = await loop.run_in_executor(
                None, ta.analyze_portfolio, portfolio, analysis_date, user_profile
            )
            # Emit each section
            for stage in stages:
                content = final_state.get(stage, "")
                yield {"data": json.dumps({"stage": stage, "content": content})}

            rid = str(uuid.uuid4())[:8]
            research_store[rid] = {
                "id": rid, **{s: final_state.get(s, "") for s in stages}
            }
            yield {"data": json.dumps({"stage": "done", "id": rid})}
        except Exception as e:
            yield {"data": json.dumps({"stage": "error", "message": str(e)})}

    return EventSourceResponse(event_generator())


# ─── Root redirect ─────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Redirect to Next.js dev server or serve legacy."""
    if os.path.isfile("frontend/index.html"):
        with open("frontend/index.html", "r") as f:
            return f.read()
    return "<html><body><h1>TradingAgents API</h1><p>Frontend at port 3000</p></body></html>"

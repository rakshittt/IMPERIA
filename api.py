import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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

# Serve the static files under "/frontend"
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("frontend/index.html", "r") as f:
        return f.read()

# Setup config
config = DEFAULT_CONFIG.copy()
# Fallback to gpt-4o-mini if not provided
config["deep_think_llm"] = os.getenv("DEEP_THINK_LLM", "gpt-4o-mini")
config["quick_think_llm"] = os.getenv("QUICK_THINK_LLM", "gpt-4o-mini")

ta = TradingAgentsGraph(debug=True, config=config)

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
        
        return JSONResponse({
            "market_report": final_state.get("market_report"),
            "sentiment_report": final_state.get("sentiment_report"),
            "news_report": final_state.get("news_report"),
            "fundamentals_report": final_state.get("fundamentals_report"),
            "macro_report": final_state.get("macro_report"),
            "research_synthesis": final_state.get("research_synthesis"),
            "trader_report": final_state.get("trader_report"),
            "risk_report": final_state.get("risk_report"),
            "final_portfolio_feedback": final_state.get("final_portfolio_feedback")
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)

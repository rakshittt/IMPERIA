import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

def main():
    portfolio = [
        {"ticker": "NVDA", "weight": 1.0, "shares": 10, "cost_basis": 100},
    ]

    user_profile = {
        "risk_tolerance": "moderate",
        "time_horizon": "1-3 years",
        "goals": "long-term growth",
        "constraints": "avoid high volatility",
    }

    print("Running TradingAgents analysis on portfolio:", json.dumps(portfolio, indent=2))
    
    ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
    
    # We will only run the news analyst and maybe some others, 
    # but the graph normally runs the configured analysts. 
    # Let's run the full analysis portfolio.
    final_state, portfolio_feedback = ta.analyze_portfolio(
        portfolio,
        "2026-05-03", # Current date
        user_profile=user_profile,
    )

    print("\n\n" + "="*50)
    print("PORTFOLIO FEEDBACK:")
    print("="*50)
    print(portfolio_feedback)

if __name__ == "__main__":
    main()

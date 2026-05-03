# TradingAgents/graph/trading_graph.py

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_utils import (
    build_portfolio_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_global_news,
    get_income_statement,
    get_indicators,
    get_insider_transactions,
    get_news,
    get_stock_data,
    normalize_portfolio,
    normalize_user_profile,
)
from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.utils import portfolio_key, safe_ticker_component
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.llm_clients import create_llm_client

from .checkpointer import checkpoint_step, clear_checkpoint, get_checkpointer, thread_id
from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .setup import GraphSetup

logger = logging.getLogger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the portfolio research agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals", "macro"],
        debug=False,
        config: Dict[str, Any] = None,
        callbacks: Optional[List] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []

        set_config(self.config)

        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        llm_kwargs = self._get_provider_kwargs()
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        self.memory_log = TradingMemoryLog(self.config)
        self.tool_nodes = self._create_tool_nodes()

        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config["max_debate_rounds"],
            max_risk_discuss_rounds=self.config["max_risk_discuss_rounds"],
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.tool_nodes,
            self.conditional_logic,
        )

        self.propagator = Propagator()

        self.curr_state = None
        self.portfolio_key = None
        self.log_states_dict = {}

        self.workflow = self.graph_setup.setup_graph(selected_analysts)
        self.graph = self.workflow.compile()
        self._checkpointer_ctx = None

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        """Get provider-specific kwargs for LLM client creation."""
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()

        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level

        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort

        elif provider == "anthropic":
            effort = self.config.get("anthropic_effort")
            if effort:
                kwargs["effort"] = effort

        return kwargs

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources using abstract methods."""
        return {
            "market": ToolNode([get_stock_data, get_indicators]),
            "social": ToolNode([get_news]),
            "news": ToolNode([get_news, get_global_news, get_insider_transactions]),
            "fundamentals": ToolNode(
                [get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_insider_transactions]
            ),
            "macro": ToolNode([get_global_news]),
        }

    def propagate(self, company_name, trade_date):
        """Backward-compatible single-holding wrapper around analyze_portfolio()."""
        return self.analyze_portfolio(
            [{"ticker": company_name, "weight": 1.0}],
            trade_date,
            user_profile=None,
        )

    def analyze_portfolio(
        self,
        portfolio: list[dict],
        analysis_date,
        user_profile: dict | None = None,
    ):
        """Run the portfolio research graph for a portfolio on a specific date."""
        normalized_portfolio = normalize_portfolio(portfolio)
        normalized_profile = normalize_user_profile(user_profile)
        key = portfolio_key(normalized_portfolio)
        self.portfolio_key = key

        if self.config.get("checkpoint_enabled"):
            self._checkpointer_ctx = get_checkpointer(self.config["data_cache_dir"], key)
            saver = self._checkpointer_ctx.__enter__()
            self.graph = self.workflow.compile(checkpointer=saver)

            step = checkpoint_step(self.config["data_cache_dir"], key, str(analysis_date))
            if step is not None:
                logger.info(
                    "Resuming from step %d for portfolio %s on %s",
                    step,
                    key,
                    analysis_date,
                )
            else:
                logger.info("Starting fresh for portfolio %s on %s", key, analysis_date)

        try:
            return self._run_graph(normalized_portfolio, str(analysis_date), normalized_profile)
        finally:
            if self._checkpointer_ctx is not None:
                self._checkpointer_ctx.__exit__(None, None, None)
                self._checkpointer_ctx = None
                self.graph = self.workflow.compile()

    def _run_graph(
        self,
        portfolio: list[dict],
        analysis_date: str,
        user_profile: dict | None = None,
    ):
        """Execute the graph and write the resulting state to disk and memory."""
        key = portfolio_key(portfolio)
        portfolio_context = build_portfolio_context(portfolio, user_profile)
        past_context = self.memory_log.get_past_context(key)
        init_agent_state = self.propagator.create_initial_state(
            portfolio,
            analysis_date,
            user_profile=user_profile,
            past_context=past_context,
        )
        args = self.propagator.get_graph_args()

        if self.config.get("checkpoint_enabled"):
            tid = thread_id(key, str(analysis_date))
            args.setdefault("config", {}).setdefault("configurable", {})["thread_id"] = tid

        if self.debug:
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                messages = chunk.get("messages", [])
                if messages:
                    messages[-1].pretty_print()
                trace.append(chunk)
            final_state = trace[-1]
        else:
            final_state = self.graph.invoke(init_agent_state, **args)

        self.curr_state = final_state
        self._log_state(analysis_date, final_state)

        self.memory_log.store_feedback(
            portfolio_key=key,
            analysis_date=analysis_date,
            portfolio_summary=portfolio_context,
            final_portfolio_feedback=final_state["final_portfolio_feedback"],
        )

        if self.config.get("checkpoint_enabled"):
            clear_checkpoint(self.config["data_cache_dir"], key, str(analysis_date))

        return final_state, final_state["final_portfolio_feedback"]

    def _log_state(self, analysis_date, final_state):
        """Log the final state to a JSON file."""
        key = final_state["portfolio_key"]
        self.log_states_dict[str(analysis_date)] = {
            "user_portfolio": final_state["user_portfolio"],
            "user_profile": final_state["user_profile"],
            "portfolio_context": final_state["portfolio_context"],
            "portfolio_key": key,
            "analysis_date": final_state["analysis_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "macro_report": final_state.get("macro_report", ""),
            "research_debate_state": final_state["research_debate_state"],
            "bullish_research": final_state["bullish_research"],
            "bearish_research": final_state["bearish_research"],
            "research_synthesis": final_state["research_synthesis"],
            "trader_report": final_state.get("trader_report", ""),
            "risk_report": final_state["risk_report"],
            "final_portfolio_feedback": final_state["final_portfolio_feedback"],
        }

        safe_key = safe_ticker_component(key, max_len=64)
        directory = Path(self.config["results_dir"]) / safe_key / "PortfolioResearch_logs"
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"full_states_log_{analysis_date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_states_dict[str(analysis_date)], f, indent=4)

    def process_signal(self, full_signal):
        """Backward-compatible adapter returning portfolio feedback unchanged."""
        return full_signal

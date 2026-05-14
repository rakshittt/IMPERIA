import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

DEFAULT_CONFIG = {
    # ── Paths ──────────────────────────────────────────────────────────────
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "sqlite_cache_path": os.getenv(
        "TRADINGAGENTS_SQLITE_CACHE",
        os.path.join(_TRADINGAGENTS_HOME, "cache", "backend_cache.sqlite3"),
    ),
    "persistence_db_path": os.getenv(
        "PERSISTENCE_DB_PATH",
        os.path.abspath(os.path.join(".", ".tradingagents_data", "user_data.db")),
    ),
    "memory_log_path": os.getenv(
        "TRADINGAGENTS_MEMORY_LOG_PATH",
        os.path.join(_TRADINGAGENTS_HOME, "memory", "portfolio_memory.md"),
    ),
    "memory_log_max_entries": None,

    # ── Runtime flags ──────────────────────────────────────────────────────
    "sec_user_agent": os.getenv("SEC_USER_AGENT", "IMPERIA/0.3.0 contact=dev@example.com"),
    "fast_query_enabled": True,
    "demo_mode": os.getenv("IMPERIA_DEMO_MODE", "false").lower() in {"1", "true", "yes", "on"},
    "api_rate_limit_per_minute": int(os.getenv("TRADINGAGENTS_API_RATE_LIMIT", "120")),

    # ── DeepSeek LLM (API backend) ─────────────────────────────────────────
    # The FastAPI backend uses DeepSeek exclusively via utils/deepseek.py.
    "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4"),

    # ── CLI / legacy graph settings ────────────────────────────────────────
    # These keys are consumed by the CLI (cli/main.py) and TradingAgentsGraph.
    # They have no effect on the FastAPI backend.
    "llm_provider": "deepseek",
    "deep_think_llm": os.getenv("DEEPSEEK_DEEP_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-v4"),
    "quick_think_llm": os.getenv("DEEPSEEK_FAST_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-v4"),
    "backend_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "checkpoint_enabled": False,
    "output_language": "English",
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
    },
    "tool_vendors": {},
}

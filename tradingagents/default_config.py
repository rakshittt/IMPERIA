import os

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "sqlite_cache_path": os.getenv(
        "TRADINGAGENTS_SQLITE_CACHE",
        os.path.join(_TRADINGAGENTS_HOME, "cache", "backend_cache.sqlite3"),
    ),
    "sec_user_agent": os.getenv(
        "SEC_USER_AGENT",
        "IMPERIA/0.3.0 contact=dev@example.com",
    ),
    "fast_query_enabled": True,
    "demo_mode": os.getenv("IMPERIA_DEMO_MODE", "false").lower() in {"1", "true", "yes", "on"},
    "enable_polymarket": os.getenv("IMPERIA_ENABLE_POLYMARKET", "false").lower() in {"1", "true", "yes", "on"},
    "api_rate_limit_per_minute": int(os.getenv("TRADINGAGENTS_API_RATE_LIMIT", "120")),
    "persistence_db_path": os.getenv(
        "PERSISTENCE_DB_PATH",
        os.path.abspath(os.path.join(".", ".tradingagents_data", "user_data.db")),
    ),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "portfolio_memory.md")),
    # Optional cap on the number of portfolio feedback memory entries. None
    # disables rotation entirely.
    "memory_log_max_entries": None,
    # LLM settings
    "llm_provider": "deepseek",
    "deep_think_llm": os.getenv("DEEPSEEK_DEEP_MODEL", "deepseek-v4-pro"),
    "quick_think_llm": os.getenv("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash"),
    # When None, each provider's client falls back to its own default endpoint
    # (api.openai.com for OpenAI, generativelanguage.googleapis.com for Gemini, ...).
    # The CLI overrides this per provider when the user picks one. Keeping a
    # provider-specific URL here would leak (e.g. OpenAI's /v1 was previously
    # being forwarded to Gemini, producing malformed request URLs).
    "backend_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Checkpoint/resume: when True, LangGraph saves state after each node
    # so a crashed run can resume from the last successful step.
    "checkpoint_enabled": False,
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}

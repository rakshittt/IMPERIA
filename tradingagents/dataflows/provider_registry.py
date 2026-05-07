"""Provider status and fallback metadata helpers for IMPERIA dataflows."""

from __future__ import annotations

import os
import importlib.util
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from tradingagents.dataflows.demo_provider import is_demo_mode
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.cache.redis_cache import redis_status


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProviderTrace:
    """Small provenance object shared by dataflows and API metadata."""

    providers_tried: list[str] = field(default_factory=list)
    providers_used: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cache_hit: bool = False
    stale: bool = False
    timestamp: str = field(default_factory=utc_now_iso)

    def try_provider(self, provider: str) -> None:
        if provider not in self.providers_tried:
            self.providers_tried.append(provider)

    def use_provider(self, provider: str) -> None:
        self.try_provider(provider)
        if provider not in self.providers_used:
            self.providers_used.append(provider)

    def warn(self, message: str) -> None:
        if message and message not in self.warnings:
            self.warnings.append(message)

    @property
    def data_quality(self) -> str:
        if self.providers_used and not self.warnings and not self.stale:
            return "good"
        if self.providers_used or self.stale:
            return "partial"
        return "poor"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["data_quality"] = self.data_quality
        return payload


OPTIONAL_PROVIDER_KEYS = {
    "Finnhub": "FINNHUB_API_KEY",
    "Alpha Vantage": "ALPHA_VANTAGE_API_KEY",
    "Financial Modeling Prep": "FINANCIAL_MODELING_PREP_API_KEY",
    "Twelve Data": "TWELVE_DATA_API_KEY",
    "EODHD": "EODHD_API_KEY",
    "NewsAPI": "NEWSAPI_API_KEY",
    "NewsData": "NEWSDATA_API_KEY",
    "TheNewsAPI": "THENEWSAPI_COM_API_TOKEN",
    "Tavily": "TAVILY_API_KEY",
    "DeepSeek": "DEEPSEEK_API_KEY",
}

REQUIRED_MODULE_STATUSES = {
    "polymarket_status": "read_only_public_endpoints",
    "form4_parser_status": "available",
    "thirteen_f_parser_status": "available",
    "analyst_consensus_status": "available_with_finnhub_or_demo",
    "peer_comparison_status": "available",
    "institutional_holder_status": "available_with_yfinance_or_demo",
    "research_streaming_status": "available",
    "llm_usage_tracking_status": "available",
    "admin_api_status": "available_local_demo_only",
    "portfolio_snapshot_status": "available",
}


def configured_provider_status() -> dict[str, Any]:
    """Return provider configuration status without exposing secret values."""

    providers = {}
    for name, env_name in OPTIONAL_PROVIDER_KEYS.items():
        if name == "TheNewsAPI":
            configured = bool(os.getenv("THENEWSAPI_COM_API_TOKEN") or os.getenv("THENEWSAPI_API_TOKEN"))
        else:
            configured = bool(os.getenv(env_name))
        providers[name] = {"configured": configured, "required": False}
    sec_user_agent = os.getenv("SEC_USER_AGENT", DEFAULT_CONFIG.get("sec_user_agent"))
    fred_configured = bool(os.getenv("FRED_API_KEY"))
    redis = redis_status()
    warnings = [] if os.getenv("SEC_USER_AGENT") else [f"SEC_USER_AGENT not set; using safe default {sec_user_agent!r}."]
    if os.getenv("IMPERIA_CACHE_BACKEND", "sqlite").lower() == "redis" and not redis.get("available"):
        warnings.append("IMPERIA_CACHE_BACKEND=redis but Redis is unavailable; local/demo endpoints should fall back or report degraded status.")
    return {
        "demo_mode": is_demo_mode(),
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4"),
        "sec_user_agent_configured": bool(os.getenv("SEC_USER_AGENT")),
        "sec_user_agent": "configured" if os.getenv("SEC_USER_AGENT") else "default_safe_fallback",
        "redis_status": redis,
        "cache_backend": os.getenv("IMPERIA_CACHE_BACKEND", "sqlite"),
        "yfinance_available": importlib.util.find_spec("yfinance") is not None,
        "sec_edgar_available": True,
        "fred_configured": fred_configured,
        "fred_status": "configured" if fred_configured else "unconfigured_graceful_degradation",
        "finnhub_configured": bool(os.getenv("FINNHUB_API_KEY")),
        "alpha_vantage_configured": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
        "fmp_configured": bool(os.getenv("FINANCIAL_MODELING_PREP_API_KEY")),
        "twelve_data_configured": bool(os.getenv("TWELVE_DATA_API_KEY")),
        "eodhd_configured": bool(os.getenv("EODHD_API_KEY")),
        "newsapi_configured": bool(os.getenv("NEWSAPI_API_KEY")),
        "newsdata_configured": bool(os.getenv("NEWSDATA_API_KEY")),
        "thenewsapi_configured": bool(os.getenv("THENEWSAPI_COM_API_TOKEN") or os.getenv("THENEWSAPI_API_TOKEN")),
        "tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
        "optional_providers": providers,
        "polymarket": {
            "enabled": True,
            "mode": "read_only_public_endpoints",
            "required_api_key": False,
        },
        **REQUIRED_MODULE_STATUSES,
        "cache_path": os.getenv("TRADINGAGENTS_SQLITE_CACHE", DEFAULT_CONFIG.get("sqlite_cache_path")),
        "warnings": warnings,
    }

"""Cache key construction helpers for IMPERIA agent and data caches."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_payload(payload: Any) -> str:
    """Hash structured input data using deterministic JSON serialization."""

    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def agent_cache_key(agent_name: str, ticker: str, intent: str, window: str, input_bundle: Any) -> str:
    """Build a safe agent cache key that changes when evidence changes."""

    input_hash = hash_payload(input_bundle)
    safe_agent = agent_name.lower().replace(" ", "_").replace("&", "and")
    return f"agent:{safe_agent}:{ticker.upper()}:{intent}:{window}:{input_hash}"

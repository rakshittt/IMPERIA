"""DeepSeek-only LLM helpers with an internal sliding-window rate limit."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Any

from tradingagents.utils.http import safe_post_json

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
FAST_MODEL = os.environ.get("DEEPSEEK_FAST_MODEL", "deepseek-v4-flash")
DEEP_MODEL = os.environ.get("DEEPSEEK_DEEP_MODEL", "deepseek-v4-pro")
DEEPSEEK_CALLS_PER_MINUTE = int(os.environ.get("DEEPSEEK_CALLS_PER_MINUTE", "20"))

_lock = threading.Lock()
_hits: deque[float] = deque()


class DeepSeekRateLimitError(RuntimeError):
    """Raised when the internal DeepSeek rate limit is exceeded."""


def _check_rate_limit() -> None:
    now = time.monotonic()
    with _lock:
        while _hits and now - _hits[0] > 60:
            _hits.popleft()
        if len(_hits) >= DEEPSEEK_CALLS_PER_MINUTE:
            raise DeepSeekRateLimitError("DeepSeek internal rate limit exceeded.")
        _hits.append(now)


def deepseek_chat(
    messages: list[dict[str, str]],
    *,
    mode: str = "fast",
    temperature: float = 0.3,
    max_tokens: int = 800,
    timeout: int = 15,
) -> dict[str, Any] | None:
    """Call DeepSeek chat completions and return sanitized JSON or ``None``."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    _check_rate_limit()
    model = FAST_MODEL if mode == "fast" else DEEP_MODEL
    started = time.perf_counter()
    payload = safe_post_json(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json_payload={
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        },
        source=f"deepseek_{mode}",
        attempts=1,
        timeout=timeout,
    )
    if payload:
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        logger.info(
            "deepseek_call mode=%s model=%s latency_ms=%d tokens_used=%s",
            mode,
            model,
            int((time.perf_counter() - started) * 1000),
            usage.get("total_tokens"),
        )
    return payload


def deepseek_text(messages: list[dict[str, str]], **kwargs: Any) -> str | None:
    """Return the assistant text from a DeepSeek response."""

    payload = deepseek_chat(messages, **kwargs)
    try:
        text = payload["choices"][0]["message"]["content"].strip() if payload else None
        return text or None
    except Exception:
        return None

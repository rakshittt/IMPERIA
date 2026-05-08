"""DeepSeek-only LLM helpers with an internal sliding-window rate limit."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from typing import Any

from tradingagents.utils.http import DEFAULT_TIMEOUT, safe_post_json

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_V4_ALIAS = "deepseek-v4"
DEEPSEEK_V4_FAST = "deepseek-v4-flash"
DEEPSEEK_V4_DEEP = "deepseek-v4-pro"

_lock = threading.Lock()
_hits: deque[float] = deque()


class DeepSeekRateLimitError(RuntimeError):
    """Raised when the internal DeepSeek rate limit is exceeded."""


def _check_rate_limit() -> None:
    now = time.monotonic()
    with _lock:
        while _hits and now - _hits[0] > 60:
            _hits.popleft()
        limit = int(os.environ.get("DEEPSEEK_CALLS_PER_MINUTE", "20"))
        if len(_hits) >= limit:
            raise DeepSeekRateLimitError("DeepSeek internal rate limit exceeded.")
        _hits.append(now)


def configured_deepseek_model() -> str:
    """Return the configured DeepSeek model name."""

    return os.environ.get("DEEPSEEK_MODEL", DEEPSEEK_V4_ALIAS)


def resolve_deepseek_model(mode: str = "fast") -> str:
    """Resolve model aliases and mode-specific overrides.

    DeepSeek's API currently exposes `deepseek-v4-flash` and
    `deepseek-v4-pro`. If `DEEPSEEK_MODEL=deepseek-v4` is used, IMPERIA
    resolves that alias by execution mode. Otherwise the configured model
    is used directly.
    """

    default_model = configured_deepseek_model()
    override = os.environ.get("DEEPSEEK_FAST_MODEL" if mode == "fast" else "DEEPSEEK_DEEP_MODEL")
    selected = (override or default_model).strip()
    if selected == DEEPSEEK_V4_ALIAS:
        return DEEPSEEK_V4_FAST if mode == "fast" else DEEPSEEK_V4_DEEP
    return selected


def deepseek_model_status() -> dict[str, Any]:
    """Return sanitized model configuration for health/admin responses."""

    default_model = configured_deepseek_model()
    return {
        "configured_model": default_model,
        "fast_model": os.environ.get("DEEPSEEK_FAST_MODEL") or default_model,
        "deep_model": os.environ.get("DEEPSEEK_DEEP_MODEL") or default_model,
        "resolved_fast_model": resolve_deepseek_model("fast"),
        "resolved_deep_model": resolve_deepseek_model("deep"),
        "thinking_mode": os.environ.get("DEEPSEEK_THINKING", "disabled"),
        "alias_resolution": "deepseek-v4 resolves to deepseek-v4-flash for fast mode and deepseek-v4-pro for deep mode.",
    }


def deepseek_chat(
    messages: list[dict[str, str]],
    *,
    mode: str = "fast",
    temperature: float = 0.3,
    max_tokens: int | None = None,
    timeout: tuple[int, int] | None = None,
    agent_name: str | None = None,
    ticker: str | None = None,
    intent: str | None = None,
    research_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any] | None:
    """Call DeepSeek chat completions and return sanitized JSON or ``None``."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    # Catch internal rate limit -- return None instead of propagating so all
    # callers get the same graceful fallback regardless of call depth.
    try:
        _check_rate_limit()
    except DeepSeekRateLimitError:
        logger.warning("deepseek_rate_limit mode=%s -- returning None to allow deterministic fallback", mode)
        return None
    model = resolve_deepseek_model(mode)
    if timeout is None:
        connect_timeout = int(os.environ.get("DEEPSEEK_TIMEOUT_CONNECT", "5"))
        read_timeout = int(os.environ.get("DEEPSEEK_FAST_TIMEOUT_READ" if mode == "fast" else "DEEPSEEK_DEEP_TIMEOUT_READ", "30" if mode == "fast" else "60"))
        timeout = (connect_timeout, read_timeout)
    attempts = int(os.environ.get("DEEPSEEK_FAST_ATTEMPTS" if mode == "fast" else "DEEPSEEK_DEEP_ATTEMPTS", "1"))
    started = time.perf_counter()
    usage: dict[str, Any] = {}
    try:
        request_payload = {
            "model": model,
            "temperature": temperature,
            "messages": messages,
        }
        if max_tokens is not None:
            request_payload["max_tokens"] = max_tokens
        thinking_mode = os.environ.get("DEEPSEEK_THINKING", "disabled").strip().lower()
        if thinking_mode in {"disabled", "enabled"}:
            request_payload["thinking"] = {"type": thinking_mode}
        payload = safe_post_json(
            f"{DEEPSEEK_BASE_URL.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json_payload=request_payload,
            source=f"deepseek_{mode}",
            attempts=attempts,
            timeout=timeout,
        )
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
    except Exception as exc:
        payload = None
        try:
            from tradingagents.persistence.usage import record_llm_usage

            record_llm_usage(
                model=model,
                agent_name=agent_name,
                ticker=ticker,
                intent=intent,
                mode=mode,
                research_id=research_id,
                request_id=request_id,
                latency_ms=int((time.perf_counter() - started) * 1000),
                success=False,
                error_message=type(exc).__name__,
            )
        except Exception:
            pass
        return None
    if payload:
        logger.info(
            "deepseek_call mode=%s model=%s latency_ms=%d tokens_used=%s",
            mode,
            model,
            int((time.perf_counter() - started) * 1000),
            usage.get("total_tokens"),
        )
    try:
        from tradingagents.persistence.usage import record_llm_usage

        record_llm_usage(
            model=model,
            agent_name=agent_name,
            ticker=ticker,
            intent=intent,
            mode=mode,
            research_id=research_id,
            request_id=request_id,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            latency_ms=int((time.perf_counter() - started) * 1000),
            success=bool(payload),
            error_message=None if payload else "empty_response",
        )
    except Exception:
        pass
    return payload


def deepseek_text(messages: list[dict[str, str]], **kwargs: Any) -> str | None:
    """Return the assistant text from a DeepSeek response."""

    payload = deepseek_chat(messages, **kwargs)
    try:
        text = payload["choices"][0]["message"]["content"].strip() if payload else None
        return text or None
    except Exception:
        return None

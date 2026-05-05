"""HTTP helpers with timeouts, retries, jitter, and sanitized logging."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = (5, 15)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _sleep(attempt: int, base_delay: float = 0.4) -> None:
    time.sleep(base_delay * (2**attempt) + random.uniform(0, 0.15))


def safe_get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    source: str = "external",
    attempts: int = 3,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
) -> Any | None:
    """GET JSON with safe retries. API keys in params/headers are never logged."""

    last_error: Exception | None = None
    started = time.perf_counter()
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            if response.status_code in {401, 403, 404}:
                return None
            if response.status_code in RETRYABLE_STATUS:
                raise RuntimeError(f"HTTP {response.status_code}")
            response.raise_for_status()
            logger.info(
                "external_api_call source=%s latency_ms=%d cache_hit=false",
                source,
                int((time.perf_counter() - started) * 1000),
            )
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                _sleep(attempt)
    logger.warning("external_api_call_failed source=%s error=%s", source, type(last_error).__name__)
    return None


def safe_post_json(
    url: str,
    *,
    json_payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    source: str = "external",
    attempts: int = 3,
    timeout: tuple[int, int] | int = DEFAULT_TIMEOUT,
) -> Any | None:
    """POST JSON with safe retries. Payloads are not logged to avoid key leaks."""

    last_error: Exception | None = None
    started = time.perf_counter()
    for attempt in range(attempts):
        try:
            response = requests.post(url, json=json_payload, headers=headers, timeout=timeout)
            if response.status_code in {401, 403, 404}:
                return None
            if response.status_code in RETRYABLE_STATUS:
                raise RuntimeError(f"HTTP {response.status_code}")
            response.raise_for_status()
            logger.info(
                "external_api_call source=%s latency_ms=%d cache_hit=false",
                source,
                int((time.perf_counter() - started) * 1000),
            )
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                _sleep(attempt)
    logger.warning("external_api_call_failed source=%s error=%s", source, type(last_error).__name__)
    return None

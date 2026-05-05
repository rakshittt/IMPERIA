"""Security headers and generic error shielding for API responses."""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative browser security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled API error path=%s", request.url.path)
            response = JSONResponse(
                {"error": "internal_server_error", "detail": "The request could not be completed."},
                status_code=500,
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

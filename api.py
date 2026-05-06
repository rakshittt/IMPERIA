"""IMPERIA compatibility shim for existing ``uvicorn api:app`` workflows."""

from tradingagents.api.main import app, create_app

__all__ = ["app", "create_app"]

"""IMPERIA compatibility shim for existing ``uvicorn api:app`` workflows."""

import os

# curl_cffi imports eventlet.tpool when eventlet is installed in the runtime.
# Eventlet's greendns monkey-patching breaks Trio/httpcore during yfinance
# imports, so disable it before any application modules can import yfinance.
os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")

from tradingagents.api.main import app, create_app

__all__ = ["app", "create_app"]

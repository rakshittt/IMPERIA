"""IMPERIA backend package."""

import os

# Keep yfinance/curl_cffi imports isolated from eventlet's greendns monkey patch
# when eventlet happens to be installed in the surrounding Python environment.
os.environ.setdefault("EVENTLET_NO_GREENDNS", "yes")

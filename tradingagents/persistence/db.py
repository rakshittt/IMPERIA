"""Backward-compatible alias for the canonical persistence module."""

from __future__ import annotations

import sys

from tradingagents.infra.db import base as _base

sys.modules[__name__] = _base

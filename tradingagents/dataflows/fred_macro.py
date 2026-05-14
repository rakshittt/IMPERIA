# Backward-compatible re-export. Import from tradingagents.providers.macro.fred for new code.
from tradingagents.providers.macro.fred import *  # noqa: F401 F403
from tradingagents.providers.macro.fred import FRED_BASE_URL, FRED_SERIES, MacroData, MacroIndicator, get_macro_indicators  # noqa: F401

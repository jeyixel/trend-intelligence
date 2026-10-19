"""Terminal logging for the optional trend-analysis trace."""
import logging

import config

LOGGER = logging.getLogger("trend_intelligence.analysis")
LOGGER.propagate = False

if config.TREND_ANALYSIS_LOGS:
    LOGGER.setLevel(logging.INFO)
    if not any(getattr(handler, "_trend_analysis_handler", False) for handler in LOGGER.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
        ))
        handler._trend_analysis_handler = True
        LOGGER.addHandler(handler)
else:
    LOGGER.disabled = True

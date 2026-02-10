"""
Logging Configuration Module for Binance Futures Trading Bot.

This module provides a centralized logging setup that all other modules
import and use. Logs are written to both the console (for real-time
monitoring) and a file (bot.log) for post-run analysis.

Usage in other modules:
    from src.logger_setup import setup_logger
    logger = setup_logger(__name__)
    logger.info("Order placed successfully")
    logger.error("Failed to connect", exc_info=True)
"""

import logging
import sys
from src.config import LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT


def setup_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger with console and file handlers.

    This function sets up a logger that outputs to:
    1. Console (stdout) — for real-time monitoring during bot execution
    2. File (bot.log)   — for persistent logging and debugging

    Args:
        name: The name for the logger, typically __name__ of the calling module.
              This appears in log messages to identify which module generated them.

    Returns:
        A configured logging.Logger instance ready for use.

    Example:
        >>> logger = setup_logger("market_orders")
        >>> logger.info("Placing BUY order for BTCUSDT")
        2024-01-15 10:30:00 - market_orders - INFO - Placing BUY order for BTCUSDT
    """
    # Create or retrieve a logger with the given name
    logger = logging.getLogger(name)

    # Only add handlers if the logger doesn't already have them.
    # This prevents duplicate log messages when setup_logger() is called
    # multiple times for the same module (e.g., during imports).
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Create formatter for consistent log message format
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        # ---------------------------------------------------------------
        # Console Handler — prints INFO and above to stdout
        # ---------------------------------------------------------------
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # ---------------------------------------------------------------
        # File Handler — writes DEBUG and above to bot.log
        # The file handler captures more detail (DEBUG level) for
        # thorough post-run analysis and debugging.
        # ---------------------------------------------------------------
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Attach both handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


# ---------------------------------------------------------------------------
# Self-test: verify logging works when this module is run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_logger = setup_logger("logger_test")
    test_logger.debug("DEBUG message — only visible in bot.log")
    test_logger.info("INFO message — visible in console and bot.log")
    test_logger.warning("WARNING message — something might need attention")
    test_logger.error("ERROR message — something went wrong")

    # Demonstrate exception logging with stack trace
    try:
        result = 1 / 0
    except ZeroDivisionError:
        test_logger.error("Exception caught with stack trace:", exc_info=True)

    print(f"\n✅ Logger test complete. Check '{LOG_FILE}' for full output.")

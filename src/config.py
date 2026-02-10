"""
Configuration Module for Binance Futures Trading Bot.

This module handles loading API credentials from environment variables,
selecting testnet vs production endpoints, and defining trading constants.
API keys are NEVER hardcoded — they are read from a .env file at runtime.
"""

import os
import sys
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# API Credentials (loaded from environment — never hardcode these!)
# ---------------------------------------------------------------------------
BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")

# Toggle between testnet and production
# Set USE_TESTNET=False in .env to switch to real trading (use with caution!)
USE_TESTNET: bool = os.getenv("USE_TESTNET", "True").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Validate that API credentials are present
# ---------------------------------------------------------------------------
if not BINANCE_API_KEY or BINANCE_API_KEY == "your_api_key_here":
    print("⚠️  WARNING: BINANCE_API_KEY is not set. Please configure your .env file.")
    print("   Copy .env.example to .env and add your API keys.")

if not BINANCE_API_SECRET or BINANCE_API_SECRET == "your_api_secret_here":
    print("⚠️  WARNING: BINANCE_API_SECRET is not set. Please configure your .env file.")
    print("   Copy .env.example to .env and add your API keys.")

# ---------------------------------------------------------------------------
# Binance Futures API Endpoints
# ---------------------------------------------------------------------------

# Testnet endpoints (safe for development and testing)
TESTNET_BASE_URL: str = "https://testnet.binancefuture.com"
TESTNET_WS_URL: str = "wss://stream.binancefuture.com"

# Production endpoints (real money — use with extreme caution!)
PRODUCTION_BASE_URL: str = "https://fapi.binance.com"
PRODUCTION_WS_URL: str = "wss://fstream.binance.com"

# Select the active endpoint based on USE_TESTNET flag
BASE_URL: str = TESTNET_BASE_URL if USE_TESTNET else PRODUCTION_BASE_URL
WS_URL: str = TESTNET_WS_URL if USE_TESTNET else PRODUCTION_WS_URL

# ---------------------------------------------------------------------------
# Trading Constants
# ---------------------------------------------------------------------------

# Default trading pair for quick testing
DEFAULT_SYMBOL: str = "BTCUSDT"

# Minimum order quantities for common pairs (Binance Futures minimums)
# These may change — always verify with get_symbol_info() for live values
MIN_QUANTITIES: dict = {
    "BTCUSDT": 0.001,
    "ETHUSDT": 0.001,
    "BNBUSDT": 0.01,
    "ADAUSDT": 1.0,
    "DOGEUSDT": 1.0,
    "SOLUSDT": 0.1,
    "XRPUSDT": 0.1,
}

# Price precision (decimal places) for common pairs
PRICE_PRECISION: dict = {
    "BTCUSDT": 2,
    "ETHUSDT": 2,
    "BNBUSDT": 2,
    "ADAUSDT": 5,
    "DOGEUSDT": 5,
    "SOLUSDT": 2,
    "XRPUSDT": 4,
}

# Quantity precision (decimal places) for common pairs
QUANTITY_PRECISION: dict = {
    "BTCUSDT": 3,
    "ETHUSDT": 3,
    "BNBUSDT": 2,
    "ADAUSDT": 0,
    "DOGEUSDT": 0,
    "SOLUSDT": 1,
    "XRPUSDT": 1,
}

# Valid order sides
VALID_SIDES: tuple = ("BUY", "SELL")

# Valid order types for Binance Futures
VALID_ORDER_TYPES: tuple = (
    "MARKET",
    "LIMIT",
    "STOP",
    "STOP_MARKET",
    "TAKE_PROFIT",
    "TAKE_PROFIT_MARKET",
)

# Rate limiting — Binance allows 1200 requests per minute for order endpoints
# We add a small buffer to stay safely under the limit
MAX_REQUESTS_PER_MINUTE: int = 1200
REQUEST_WEIGHT_BUFFER: int = 100  # Keep 100 request weight as safety margin

# ---------------------------------------------------------------------------
# Logging Configuration Constants
# ---------------------------------------------------------------------------
LOG_FILE: str = "bot.log"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Helper function to display current configuration (without exposing secrets)
# ---------------------------------------------------------------------------
def print_config() -> None:
    """Print the current configuration to the console (masks API keys)."""
    masked_key = BINANCE_API_KEY[:4] + "****" if len(BINANCE_API_KEY) > 4 else "NOT SET"
    env_mode = "TESTNET" if USE_TESTNET else "⚠️  PRODUCTION"

    print("=" * 60)
    print("  Binance Futures Trading Bot — Configuration")
    print("=" * 60)
    print(f"  Environment : {env_mode}")
    print(f"  API Key     : {masked_key}")
    print(f"  Base URL    : {BASE_URL}")
    print(f"  Log File    : {LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    # When run directly, display the current configuration
    print_config()

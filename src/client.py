"""
Binance API Client Wrapper for Futures Trading.

This module provides a BinanceClient class that wraps the python-binance
library specifically for USDT-M Futures operations. It centralizes all
API interactions, handles exceptions, and provides consistent logging.

The client automatically connects to either the Testnet or Production
endpoint based on the USE_TESTNET flag in config.py.

Trading Concepts:
    - USDT-M Futures: Futures contracts margined and settled in USDT.
    - Mark Price: The price used by Binance to calculate unrealized PnL
      and liquidation. Based on index price + funding basis.
    - Leverage: Multiplier for position size. Higher leverage = higher
      risk and potential reward.

Usage:
    from src.client import BinanceClient
    client = BinanceClient()
    price = client.get_current_price("BTCUSDT")
    balance = client.get_account_balance()
"""

import time
from typing import Any, Dict, List, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from src.config import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    USE_TESTNET,
    TESTNET_BASE_URL,
)
from src.logger_setup import setup_logger

# Module-level logger
logger = setup_logger(__name__)


class BinanceClient:
    """
    Wrapper around the Binance Futures API client.

    This class provides a clean interface for common Futures operations:
    - Fetching account balance and symbol information
    - Getting current market prices
    - Placing, cancelling, and querying orders
    - Handling API errors consistently

    All methods include error handling and logging for reliable operation.

    Attributes:
        client: The underlying python-binance Client instance.
    """

    def __init__(self) -> None:
        """
        Initialize the Binance Futures client.

        Connects to either the Testnet or Production API based on the
        USE_TESTNET configuration flag. Logs the connection status.

        Raises:
            BinanceAPIException: If the API keys are invalid.
            BinanceRequestException: If there's a network connectivity issue.
        """
        try:
            self.client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

            if USE_TESTNET:
                # Override the Futures base URL to point to Testnet
                self.client.FUTURES_URL = TESTNET_BASE_URL + "/fapi"
                logger.info("Connected to Binance Futures TESTNET")
            else:
                logger.warning(
                    "⚠️  Connected to Binance Futures PRODUCTION — real money at risk!"
                )

            logger.info("BinanceClient initialized successfully")

        except BinanceAPIException as e:
            logger.error(f"API authentication failed: {e.message}", exc_info=True)
            raise
        except BinanceRequestException as e:
            logger.error(f"Network error during initialization: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during client init: {e}", exc_info=True)
            raise

    # -------------------------------------------------------------------
    # Account Information Methods
    # -------------------------------------------------------------------

    def get_account_balance(self, asset: str = "USDT") -> Optional[Dict[str, Any]]:
        """
        Get the futures account balance for a specific asset.

        Args:
            asset: The asset to query (default: "USDT").

        Returns:
            A dictionary with balance details including:
            - 'asset': The asset name
            - 'balance': Total balance
            - 'availableBalance': Balance available for trading
            Returns None if the asset is not found or an error occurs.

        Example:
            >>> client = BinanceClient()
            >>> balance = client.get_account_balance("USDT")
            >>> print(f"Available: {balance['availableBalance']} USDT")
        """
        try:
            balances = self.client.futures_account_balance()
            for bal in balances:
                if bal["asset"] == asset:
                    logger.info(
                        f"Balance for {asset}: "
                        f"Total={bal['balance']}, "
                        f"Available={bal['availableBalance']}"
                    )
                    return bal

            logger.warning(f"Asset '{asset}' not found in account balances")
            return None

        except BinanceAPIException as e:
            logger.error(f"API error fetching balance: {e.message}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error fetching balance: {e}", exc_info=True)
            return None

    # -------------------------------------------------------------------
    # Market Data Methods
    # -------------------------------------------------------------------

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get trading rules and filters for a specific symbol.

        This returns information needed for order placement:
        - Minimum quantity (LOT_SIZE filter)
        - Price precision (PRICE_FILTER)
        - Tick size and step size

        Args:
            symbol: The trading pair symbol (e.g., "BTCUSDT").

        Returns:
            A dictionary with the full symbol information from Binance,
            or None if the symbol is not found or an error occurs.

        Example:
            >>> info = client.get_symbol_info("BTCUSDT")
            >>> print(info['filters'])  # Contains LOT_SIZE, PRICE_FILTER, etc.
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info["symbols"]:
                if s["symbol"] == symbol:
                    logger.info(f"Retrieved symbol info for {symbol}")
                    return s

            logger.warning(f"Symbol '{symbol}' not found on Binance Futures")
            return None

        except BinanceAPIException as e:
            logger.error(
                f"API error fetching symbol info for {symbol}: {e.message}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching symbol info: {e}", exc_info=True)
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get the current market price (last traded price) for a symbol.

        This uses the Futures mark price endpoint which provides:
        - markPrice: Used for PnL and liquidation calculations
        - lastFundingRate: Current funding rate
        - nextFundingTime: When the next funding occurs

        Args:
            symbol: The trading pair symbol (e.g., "BTCUSDT").

        Returns:
            The current price as a float, or None if an error occurs.

        Example:
            >>> price = client.get_current_price("BTCUSDT")
            >>> print(f"BTC is currently ${price:,.2f}")
        """
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            logger.info(f"Current price for {symbol}: {price}")
            return price

        except BinanceAPIException as e:
            logger.error(
                f"API error fetching price for {symbol}: {e.message}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}", exc_info=True)
            return None

    # -------------------------------------------------------------------
    # Order Management Methods
    # -------------------------------------------------------------------

    def place_order(self, **params) -> Optional[Dict[str, Any]]:
        """
        Place a Futures order with the given parameters.

        This is the central order placement method used by all order types.
        It passes parameters directly to the Binance Futures create_order
        endpoint.

        Common parameters:
            symbol (str):       Trading pair (e.g., "BTCUSDT")
            side (str):         "BUY" or "SELL"
            type (str):         Order type (MARKET, LIMIT, STOP, etc.)
            quantity (float):   Amount to trade
            price (float):     Limit price (for LIMIT orders)
            stopPrice (float): Trigger price (for STOP orders)
            timeInForce (str): GTC, IOC, FOK (for LIMIT orders)

        Args:
            **params: Keyword arguments passed to futures_create_order().

        Returns:
            The order response dictionary from Binance containing:
            - orderId, symbol, status, type, side, price, origQty, etc.
            Returns None if the order fails.

        Example:
            >>> order = client.place_order(
            ...     symbol="BTCUSDT",
            ...     side="BUY",
            ...     type="MARKET",
            ...     quantity=0.001
            ... )
            >>> print(f"Order ID: {order['orderId']}")
        """
        try:
            logger.info(f"Placing order: {params}")
            order = self.client.futures_create_order(**params)
            logger.info(
                f"Order placed successfully: "
                f"ID={order.get('orderId')}, "
                f"Symbol={order.get('symbol')}, "
                f"Side={order.get('side')}, "
                f"Type={order.get('type')}, "
                f"Status={order.get('status')}"
            )
            return order

        except BinanceAPIException as e:
            logger.error(
                f"API error placing order: {e.message} (Code: {e.code})",
                exc_info=True,
            )
            return None
        except BinanceRequestException as e:
            logger.error(f"Network error placing order: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}", exc_info=True)
            return None

    def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """
        Cancel an open Futures order by its order ID.

        Args:
            symbol:   The trading pair symbol (e.g., "BTCUSDT").
            order_id: The order ID to cancel (from the place_order response).

        Returns:
            The cancellation response dictionary, or None if it fails.

        Example:
            >>> result = client.cancel_order("BTCUSDT", 123456789)
            >>> print(f"Cancelled: {result['status']}")
        """
        try:
            logger.info(f"Cancelling order {order_id} for {symbol}")
            result = self.client.futures_cancel_order(
                symbol=symbol, orderId=order_id
            )
            logger.info(
                f"Order {order_id} cancelled: status={result.get('status')}"
            )
            return result

        except BinanceAPIException as e:
            logger.error(
                f"API error cancelling order {order_id}: {e.message}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}", exc_info=True)
            return None

    def get_order_status(
        self, symbol: str, order_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a Futures order.

        Possible statuses:
        - NEW: Order has been accepted but not yet filled
        - PARTIALLY_FILLED: Part of the order has been executed
        - FILLED: The entire order has been executed
        - CANCELED: The order was cancelled by the user
        - REJECTED: The order was rejected by the engine
        - EXPIRED: The order has expired (e.g., time-in-force)

        Args:
            symbol:   The trading pair symbol (e.g., "BTCUSDT").
            order_id: The order ID to query.

        Returns:
            The order status dictionary, or None if an error occurs.

        Example:
            >>> status = client.get_order_status("BTCUSDT", 123456789)
            >>> print(f"Status: {status['status']}")
        """
        try:
            order = self.client.futures_get_order(
                symbol=symbol, orderId=order_id
            )
            logger.info(
                f"Order {order_id} status: {order.get('status')}, "
                f"Filled: {order.get('executedQty')}/{order.get('origQty')}"
            )
            return order

        except BinanceAPIException as e:
            logger.error(
                f"API error fetching order {order_id}: {e.message}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(f"Error fetching order status: {e}", exc_info=True)
            return None

    def cancel_all_open_orders(self, symbol: str) -> bool:
        """
        Cancel all open orders for a given symbol.

        Useful for cleaning up when a strategy is stopped or when
        switching between strategies.

        Args:
            symbol: The trading pair symbol (e.g., "BTCUSDT").

        Returns:
            True if all orders were cancelled, False if an error occurred.
        """
        try:
            logger.info(f"Cancelling all open orders for {symbol}")
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            logger.info(f"All open orders for {symbol} cancelled successfully")
            return True

        except BinanceAPIException as e:
            logger.error(
                f"API error cancelling all orders for {symbol}: {e.message}",
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}", exc_info=True)
            return False

    def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get all open (unfilled) orders for a symbol.

        Args:
            symbol: The trading pair symbol (e.g., "BTCUSDT").

        Returns:
            A list of open order dictionaries, or an empty list on error.
        """
        try:
            orders = self.client.futures_get_open_orders(symbol=symbol)
            logger.info(f"Found {len(orders)} open orders for {symbol}")
            return orders

        except BinanceAPIException as e:
            logger.error(
                f"API error fetching open orders: {e.message}", exc_info=True
            )
            return []
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}", exc_info=True)
            return []


# ---------------------------------------------------------------------------
# Self-test: verify client initialization when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  BinanceClient — Connection Test")
    print("=" * 60)

    try:
        client = BinanceClient()
        print("✅ Client initialized successfully")

        # Try to fetch current BTC price
        price = client.get_current_price("BTCUSDT")
        if price:
            print(f"✅ BTCUSDT current price: ${price:,.2f}")
        else:
            print("⚠️  Could not fetch price (check API keys)")

        # Try to fetch account balance
        balance = client.get_account_balance()
        if balance:
            print(f"✅ USDT Balance: {balance['balance']}")
        else:
            print("⚠️  Could not fetch balance (check API keys)")

    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        print("   Make sure your .env file has valid API keys.")

    print("=" * 60)

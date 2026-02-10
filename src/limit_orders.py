"""
Limit Order Module for Binance Futures Trading Bot.

A limit order lets you specify the EXACT price at which you want to buy
or sell. Unlike market orders, limit orders are NOT guaranteed to execute —
they only fill when the market reaches your specified price.

When to use limit orders:
    - When you want to buy at a lower price than the current market price
    - When you want to sell at a higher price than the current market price
    - When you want to control your entry/exit price precisely
    - When you're willing to wait for the price to reach your target

Time-in-Force (TIF):
    - GTC (Good-Till-Cancelled): Stays open until filled or manually cancelled.
      This is the default and most common setting.
    - IOC (Immediate-Or-Cancel): Fills as much as possible immediately,
      cancels any unfilled portion.
    - FOK (Fill-Or-Kill): Must fill the entire quantity immediately or
      the entire order is cancelled.

CLI Usage:
    python -m src.limit_orders BTCUSDT BUY 0.001 50000
    python -m src.limit_orders ETHUSDT SELL 0.01 4000

Module Usage:
    from src.limit_orders import LimitOrder
    order = LimitOrder("BTCUSDT", "BUY", 0.001, 50000.0)
    result = order.execute()
"""

import sys
import argparse
from typing import Any, Dict, Optional

from src.client import BinanceClient
from src.logger_setup import setup_logger
from src.validators import (
    validate_symbol,
    validate_side,
    validate_quantity,
    validate_price,
)

# Module-level logger
logger = setup_logger(__name__)


class LimitOrder:
    """
    Represents a Binance Futures limit order.

    A limit order is placed at a specific price and waits in the order book
    until the market price reaches it. If the market never reaches the limit
    price, the order remains open (with GTC) until manually cancelled.

    Attributes:
        symbol:        The trading pair (e.g., "BTCUSDT").
        side:          "BUY" or "SELL".
        quantity:      The amount to trade.
        price:         The limit price at which to execute.
        time_in_force: How long the order stays active (default: GTC).
        client:        The BinanceClient instance for API calls.
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
    ) -> None:
        """
        Initialize a LimitOrder with validated parameters.

        Args:
            symbol:        Trading pair symbol (e.g., "BTCUSDT").
            side:          Order side — "BUY" or "SELL".
            quantity:      Amount to trade (must be > 0).
            price:         Limit price (must be > 0).
            time_in_force: Order duration — "GTC", "IOC", or "FOK" (default: GTC).

        Raises:
            ValueError: If any parameter fails validation.
        """
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.quantity = float(quantity)
        self.price = float(price)
        self.time_in_force = time_in_force.upper()
        self.client = BinanceClient()

        logger.info(
            f"Initializing LimitOrder: {self.side} {self.quantity} {self.symbol} "
            f"@ ${self.price:,.2f} (TIF: {self.time_in_force})"
        )
        self._validate()

    def _validate(self) -> None:
        """Validate all order parameters including price reasonableness."""
        logger.info("Validating limit order parameters...")
        validate_symbol(self.symbol)
        validate_side(self.side)
        validate_quantity(self.quantity)
        validate_price(self.price)

        # Validate time-in-force
        valid_tifs = ("GTC", "IOC", "FOK")
        if self.time_in_force not in valid_tifs:
            raise ValueError(
                f"Time-in-force must be one of {valid_tifs}. "
                f"Got '{self.time_in_force}'."
            )

        # Check price reasonableness against current market price
        current_price = self.client.get_current_price(self.symbol)
        if current_price:
            deviation = abs(self.price - current_price) / current_price * 100
            if deviation > 50:
                logger.warning(
                    f"⚠️  Limit price ${self.price:,.2f} is {deviation:.1f}% away "
                    f"from current price ${current_price:,.2f}. "
                    f"This order may never fill."
                )
                print(
                    f"\n⚠️  Warning: Your limit price is {deviation:.1f}% away "
                    f"from the current market price. The order may take a long "
                    f"time to fill or may never fill."
                )

        logger.info("All parameters validated successfully")

    def execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute the limit order on Binance Futures.

        This method:
        1. Logs the order details
        2. Places the limit order with GTC time-in-force
        3. Returns the order response including the order ID

        Returns:
            The order response dictionary from Binance if successful.
            Returns None on failure.
        """
        try:
            logger.info(
                f"Executing limit order: {self.side} {self.quantity} {self.symbol} "
                f"@ ${self.price:,.2f}"
            )

            # Place the limit order
            # For limit orders, we MUST specify:
            #   - type=LIMIT
            #   - price: the limit price
            #   - timeInForce: how long the order stays active
            result = self.client.place_order(
                symbol=self.symbol,
                side=self.side,
                type="LIMIT",
                quantity=self.quantity,
                price=self.price,
                timeInForce=self.time_in_force,
            )

            if result:
                order_id = result.get("orderId")
                status = result.get("status")
                logger.info(
                    f"✅ Limit order placed successfully!\n"
                    f"   Order ID    : {order_id}\n"
                    f"   Symbol      : {result.get('symbol')}\n"
                    f"   Side        : {result.get('side')}\n"
                    f"   Quantity    : {result.get('origQty')}\n"
                    f"   Price       : {result.get('price')}\n"
                    f"   TIF         : {self.time_in_force}\n"
                    f"   Status      : {status}"
                )
                print(f"\n✅ Limit Order Placed Successfully!")
                print(f"   Order ID    : {order_id}")
                print(f"   Symbol      : {result.get('symbol')}")
                print(f"   Side        : {result.get('side')}")
                print(f"   Quantity    : {result.get('origQty')}")
                print(f"   Price       : ${float(result.get('price', 0)):,.2f}")
                print(f"   TIF         : {self.time_in_force}")
                print(f"   Status      : {status}")

                if status == "NEW":
                    print(
                        f"\n   ℹ️  Order is waiting in the order book. "
                        f"It will fill when the market reaches ${self.price:,.2f}."
                    )

                return result
            else:
                logger.error("Limit order failed — no response from API")
                print("\n❌ Limit order failed. Check bot.log for details.")
                return None

        except Exception as e:
            logger.error(f"Error executing limit order: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return None


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for limit order execution."""
    parser = argparse.ArgumentParser(
        description="Place a Limit Order on Binance Futures",
        epilog=(
            "Examples:\n"
            "  python -m src.limit_orders BTCUSDT BUY 0.001 50000\n"
            "  python -m src.limit_orders ETHUSDT SELL 0.01 4000\n"
            "\n"
            "Time-in-Force options:\n"
            "  GTC = Good-Till-Cancelled (default, stays open until filled)\n"
            "  IOC = Immediate-Or-Cancel (fill what you can, cancel rest)\n"
            "  FOK = Fill-Or-Kill (fill all or nothing)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "symbol",
        type=str,
        help="Trading pair symbol (e.g., BTCUSDT)",
    )
    parser.add_argument(
        "side",
        type=str,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side: BUY or SELL",
    )
    parser.add_argument(
        "quantity",
        type=float,
        help="Quantity to trade (e.g., 0.001 for BTC)",
    )
    parser.add_argument(
        "price",
        type=float,
        help="Limit price in USDT (e.g., 50000 for $50,000)",
    )
    parser.add_argument(
        "--tif",
        type=str,
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force (default: GTC)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for CLI execution."""
    print("=" * 60)
    print("  Binance Futures — Limit Order")
    print("=" * 60)

    try:
        args = parse_arguments()
        order = LimitOrder(
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.tif,
        )
        result = order.execute()
        sys.exit(0 if result else 1)

    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Order cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Stop-Limit Order Module for Binance Futures Trading Bot.

A stop-limit order is a TWO-STAGE conditional order:

Stage 1 — Trigger:
    The order sits dormant until the market price reaches the "stop price".
    At this point, the order is "activated" and becomes a regular limit order.

Stage 2 — Execution:
    Once activated, the order behaves as a limit order at the "limit price".
    It will only fill at the limit price or better.

How stop_price and limit_price work together:
    - stop_price:  The trigger price. When the market reaches this level,
                   the limit order is placed.
    - limit_price: The actual price of the limit order that gets placed
                   once the stop is triggered.

Example — Protecting a LONG position (stop-loss):
    You bought BTC at $60,000 and want to limit losses if price drops.
    - stop_price  = $58,000 (trigger when price falls to this level)
    - limit_price = $57,800 (sell at this price or better after trigger)
    - side        = SELL

Example — Entering on a breakout:
    BTC is at $59,000, you want to buy if it breaks above $60,000.
    - stop_price  = $60,000 (trigger on breakout)
    - limit_price = $60,200 (buy at this price or better)
    - side        = BUY

Note on Binance Futures:
    We use the "STOP" order type which combines stop trigger + limit execution.
    For pure stop-market (no limit price), Binance Futures offers "STOP_MARKET".

CLI Usage:
    python -m src.advanced.stop_limit BTCUSDT SELL 0.001 58000 57800
    python -m src.advanced.stop_limit ETHUSDT BUY 0.01 4100 4120

Module Usage:
    from src.advanced.stop_limit import StopLimitOrder
    order = StopLimitOrder("BTCUSDT", "SELL", 0.001, 58000, 57800)
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


class StopLimitOrder:
    """
    Represents a Binance Futures stop-limit order.

    This is a conditional order with two price levels:
    1. stop_price  — the trigger price (activates the order)
    2. limit_price — the execution price (the limit order placed after trigger)

    The relationship between stop and limit prices:
    - For SELL orders: stop_price >= limit_price (stop triggers, sells at limit or higher)
    - For BUY orders:  stop_price <= limit_price (stop triggers, buys at limit or lower)

    Attributes:
        symbol:      Trading pair (e.g., "BTCUSDT").
        side:        "BUY" or "SELL".
        quantity:    Amount to trade.
        stop_price:  Price at which the order is triggered.
        limit_price: Price at which the limit order is placed.
        client:      BinanceClient instance.
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float,
    ) -> None:
        """
        Initialize a StopLimitOrder with validated parameters.

        Args:
            symbol:      Trading pair (e.g., "BTCUSDT").
            side:        "BUY" or "SELL".
            quantity:    Amount to trade (must be > 0).
            stop_price:  Trigger price (must be > 0).
            limit_price: Limit execution price (must be > 0).

        Raises:
            ValueError: If parameters fail validation or have illogical relationships.
        """
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.quantity = float(quantity)
        self.stop_price = float(stop_price)
        self.limit_price = float(limit_price)
        self.client = BinanceClient()

        logger.info(
            f"Initializing StopLimitOrder: {self.side} {self.quantity} {self.symbol} "
            f"stop={self.stop_price} limit={self.limit_price}"
        )
        self._validate()

    def _validate(self) -> None:
        """
        Validate all order parameters and their logical relationships.

        The stop and limit prices must have a logical relationship:
        - SELL stop-limit: stop_price should be >= limit_price
          (trigger at stop, willing to sell down to limit)
        - BUY stop-limit: stop_price should be <= limit_price
          (trigger at stop, willing to buy up to limit)
        """
        logger.info("Validating stop-limit order parameters...")
        validate_symbol(self.symbol)
        validate_side(self.side)
        validate_quantity(self.quantity)
        validate_price(self.stop_price)
        validate_price(self.limit_price)

        # Validate logical relationship between stop and limit prices
        if self.side == "SELL":
            if self.limit_price > self.stop_price:
                raise ValueError(
                    f"For SELL stop-limit orders, limit_price ({self.limit_price}) "
                    f"should be <= stop_price ({self.stop_price}). "
                    f"The limit price is the minimum price you're willing to sell at "
                    f"after the stop triggers."
                )
        elif self.side == "BUY":
            if self.limit_price < self.stop_price:
                raise ValueError(
                    f"For BUY stop-limit orders, limit_price ({self.limit_price}) "
                    f"should be >= stop_price ({self.stop_price}). "
                    f"The limit price is the maximum price you're willing to buy at "
                    f"after the stop triggers."
                )

        logger.info("All parameters validated successfully")

    def execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute the stop-limit order on Binance Futures.

        Uses the "STOP" order type which places a limit order when the
        stop price is reached.

        Returns:
            The order response dictionary from Binance, or None on failure.
        """
        try:
            logger.info(
                f"Placing stop-limit order: {self.side} {self.quantity} {self.symbol} "
                f"stop={self.stop_price} limit={self.limit_price}"
            )

            # Fetch current price for context
            current_price = self.client.get_current_price(self.symbol)
            if current_price:
                logger.info(f"Current {self.symbol} price: ${current_price:,.2f}")

            # Place the stop-limit order
            # Order type "STOP" on Binance Futures = Stop-Limit order
            # It requires: stopPrice (trigger) + price (limit) + timeInForce
            result = self.client.place_order(
                symbol=self.symbol,
                side=self.side,
                type="STOP",
                quantity=self.quantity,
                price=self.limit_price,
                stopPrice=self.stop_price,
                timeInForce="GTC",
            )

            if result:
                logger.info(
                    f"✅ Stop-limit order placed successfully!\n"
                    f"   Order ID    : {result.get('orderId')}\n"
                    f"   Symbol      : {result.get('symbol')}\n"
                    f"   Side        : {result.get('side')}\n"
                    f"   Quantity    : {result.get('origQty')}\n"
                    f"   Stop Price  : {result.get('stopPrice')} (trigger)\n"
                    f"   Limit Price : {result.get('price')} (execution)\n"
                    f"   Status      : {result.get('status')}"
                )
                print(f"\n✅ Stop-Limit Order Placed Successfully!")
                print(f"   Order ID    : {result.get('orderId')}")
                print(f"   Symbol      : {result.get('symbol')}")
                print(f"   Side        : {result.get('side')}")
                print(f"   Quantity    : {result.get('origQty')}")
                print(f"   Stop Price  : ${float(result.get('stopPrice', 0)):,.2f} (trigger)")
                print(f"   Limit Price : ${float(result.get('price', 0)):,.2f} (execution)")
                print(f"   Status      : {result.get('status')}")
                print(
                    f"\n   ℹ️  This order will activate when the price reaches "
                    f"${self.stop_price:,.2f}, then place a limit order at "
                    f"${self.limit_price:,.2f}."
                )
                return result
            else:
                logger.error("Stop-limit order failed — no response from API")
                print("\n❌ Stop-limit order failed. Check bot.log for details.")
                return None

        except Exception as e:
            logger.error(f"Error executing stop-limit order: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return None


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for stop-limit order."""
    parser = argparse.ArgumentParser(
        description="Place a Stop-Limit Order on Binance Futures",
        epilog=(
            "How it works:\n"
            "  1. Order waits dormant until market reaches STOP_PRICE\n"
            "  2. Once triggered, a limit order is placed at LIMIT_PRICE\n"
            "  3. The limit order fills at LIMIT_PRICE or better\n"
            "\n"
            "Examples:\n"
            "  # Stop-loss for a long position (sell if price drops)\n"
            "  python -m src.advanced.stop_limit BTCUSDT SELL 0.001 58000 57800\n"
            "\n"
            "  # Buy on breakout (buy if price rises above level)\n"
            "  python -m src.advanced.stop_limit BTCUSDT BUY 0.001 62000 62200\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", type=str, help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument(
        "side", type=str, choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL"
    )
    parser.add_argument("quantity", type=float, help="Quantity to trade")
    parser.add_argument(
        "stop_price", type=float, help="Trigger price (activates the order)"
    )
    parser.add_argument(
        "limit_price", type=float, help="Limit price (execution price after trigger)"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for CLI execution."""
    print("=" * 60)
    print("  Binance Futures — Stop-Limit Order")
    print("=" * 60)

    try:
        args = parse_arguments()
        order = StopLimitOrder(
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            stop_price=args.stop_price,
            limit_price=args.limit_price,
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

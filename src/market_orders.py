"""
Market Order Module for Binance Futures Trading Bot.

A market order is the simplest order type — it executes immediately at the
current market price. It guarantees execution but NOT a specific price.

When to use market orders:
    - When you need immediate execution (e.g., urgent entries/exits)
    - When the asset has high liquidity (tight bid-ask spread)
    - When you prioritize speed over price

Risks:
    - Slippage: In volatile markets, the fill price may differ from the
      price you saw when placing the order.
    - No price guarantee: You get whatever the market price is at execution.

CLI Usage:
    python -m src.market_orders BTCUSDT BUY 0.001
    python -m src.market_orders ETHUSDT SELL 0.01

Module Usage:
    from src.market_orders import MarketOrder
    order = MarketOrder("BTCUSDT", "BUY", 0.001)
    result = order.execute()
"""

import sys
import argparse
from typing import Any, Dict, Optional

from src.client import BinanceClient
from src.logger_setup import setup_logger
from src.validators import validate_symbol, validate_side, validate_quantity

# Module-level logger
logger = setup_logger(__name__)


class MarketOrder:
    """
    Represents a Binance Futures market order.

    A market order buys or sells an asset immediately at the best
    available price. It is the fastest way to enter or exit a position.

    Attributes:
        symbol:   The trading pair (e.g., "BTCUSDT").
        side:     "BUY" for long / close short, "SELL" for short / close long.
        quantity: The amount to trade.
        client:   The BinanceClient instance used for API calls.
    """

    def __init__(self, symbol: str, side: str, quantity: float) -> None:
        """
        Initialize a MarketOrder with validated parameters.

        Args:
            symbol:   Trading pair symbol (e.g., "BTCUSDT").
            side:     Order side — "BUY" or "SELL".
            quantity: Amount to trade (must be > 0).

        Raises:
            ValueError: If any parameter fails validation.
        """
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.quantity = float(quantity)
        self.client = BinanceClient()

        # Validate all inputs before anything else
        logger.info(
            f"Initializing MarketOrder: {self.side} {self.quantity} {self.symbol}"
        )
        self._validate()

    def _validate(self) -> None:
        """Validate all order parameters."""
        logger.info("Validating market order parameters...")
        validate_symbol(self.symbol)
        validate_side(self.side)
        validate_quantity(self.quantity)
        logger.info("All parameters validated successfully")

    def execute(self) -> Optional[Dict[str, Any]]:
        """
        Execute the market order on Binance Futures.

        This method:
        1. Logs the order details
        2. Fetches the current price for reference
        3. Places the market order via the BinanceClient
        4. Logs and returns the result

        Returns:
            The order response dictionary from Binance if successful,
            containing orderId, status, fills, etc. Returns None on failure.

        Example:
            >>> order = MarketOrder("BTCUSDT", "BUY", 0.001)
            >>> result = order.execute()
            >>> if result:
            ...     print(f"Order filled at {result['avgPrice']}")
        """
        try:
            # Step 1: Log the order we're about to place
            logger.info(
                f"Executing market order: {self.side} {self.quantity} {self.symbol}"
            )

            # Step 2: Fetch current price for reference logging
            current_price = self.client.get_current_price(self.symbol)
            if current_price:
                logger.info(
                    f"Current {self.symbol} price: ${current_price:,.2f} "
                    f"(reference only — market orders fill at best available)"
                )

            # Step 3: Place the market order
            result = self.client.place_order(
                symbol=self.symbol,
                side=self.side,
                type="MARKET",
                quantity=self.quantity,
            )

            # Step 4: Process the result
            if result:
                logger.info(
                    f"✅ Market order executed successfully!\n"
                    f"   Order ID    : {result.get('orderId')}\n"
                    f"   Symbol      : {result.get('symbol')}\n"
                    f"   Side        : {result.get('side')}\n"
                    f"   Quantity    : {result.get('origQty')}\n"
                    f"   Status      : {result.get('status')}\n"
                    f"   Avg Price   : {result.get('avgPrice', 'N/A')}"
                )
                print(f"\n✅ Market Order Executed Successfully!")
                print(f"   Order ID    : {result.get('orderId')}")
                print(f"   Symbol      : {result.get('symbol')}")
                print(f"   Side        : {result.get('side')}")
                print(f"   Quantity    : {result.get('origQty')}")
                print(f"   Status      : {result.get('status')}")
                print(f"   Avg Price   : {result.get('avgPrice', 'N/A')}")
                return result
            else:
                logger.error("Market order failed — no response from API")
                print("\n❌ Market order failed. Check bot.log for details.")
                return None

        except Exception as e:
            logger.error(f"Error executing market order: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return None


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for market order execution."""
    parser = argparse.ArgumentParser(
        description="Place a Market Order on Binance Futures",
        epilog=(
            "Examples:\n"
            "  python -m src.market_orders BTCUSDT BUY 0.001\n"
            "  python -m src.market_orders ETHUSDT SELL 0.01\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "symbol",
        type=str,
        help="Trading pair symbol (e.g., BTCUSDT, ETHUSDT)",
    )
    parser.add_argument(
        "side",
        type=str,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side: BUY (go long) or SELL (go short)",
    )
    parser.add_argument(
        "quantity",
        type=float,
        help="Quantity to trade (e.g., 0.001 for BTC)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for CLI execution."""
    print("=" * 60)
    print("  Binance Futures — Market Order")
    print("=" * 60)

    try:
        args = parse_arguments()
        order = MarketOrder(
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
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

"""
Grid Trading Strategy for Binance Futures Trading Bot.

Grid trading places a series of buy and sell limit orders at predefined
price levels (the "grid") within a price range. It profits from price
oscillations within the range.

How Grid Trading Works:
    1. Define a price range: lower_bound to upper_bound
    2. Divide the range into N evenly spaced grid levels
    3. Place BUY limit orders at levels below the current price
    4. Place SELL limit orders at levels above the current price
    5. When a BUY fills → place a SELL order one grid level above
    6. When a SELL fills → place a BUY order one grid level below

Profit Mechanism:
    Each completed buy-sell cycle captures the spread between grid levels.
    The more the price oscillates within the range, the more profit.

Best Market Conditions:
    - Sideways / ranging markets (price bouncing between support & resistance)
    - NOT suitable for strong trends (price moves outside the grid)

Risks:
    - If price breaks below the grid, you're left holding losing long positions
    - If price breaks above the grid, you miss out on upside gains
    - Requires sufficient capital to fund all grid orders

CLI Usage:
    python -m src.advanced.grid BTCUSDT 58000 62000 10 0.001
    (Grid from $58k-$62k with 10 levels, 0.001 BTC per grid)
"""

import sys
import time
import argparse
from typing import Any, Dict, List, Optional

from src.client import BinanceClient
from src.logger_setup import setup_logger
from src.validators import validate_symbol, validate_quantity, validate_price

logger = setup_logger(__name__)

# Monitoring poll interval in seconds
POLL_INTERVAL: int = 10


class GridStrategy:
    """
    Grid trading strategy for Binance Futures.

    Places buy/sell limit orders at evenly spaced price levels and
    manages the grid by replacing filled orders.

    Attributes:
        symbol:            Trading pair (e.g., "BTCUSDT").
        price_lower:       Lower bound of the grid.
        price_upper:       Upper bound of the grid.
        num_grids:         Number of grid levels.
        quantity_per_grid: Quantity for each grid order.
        grid_levels:       Calculated price levels.
        active_orders:     Dict mapping grid_level -> order info.
    """

    def __init__(
        self, symbol: str, price_lower: float, price_upper: float,
        num_grids: int, quantity_per_grid: float,
    ) -> None:
        """Initialize grid strategy and calculate grid levels."""
        self.symbol = symbol.upper()
        self.price_lower = float(price_lower)
        self.price_upper = float(price_upper)
        self.num_grids = int(num_grids)
        self.quantity_per_grid = float(quantity_per_grid)
        self.client = BinanceClient()
        self.active_orders: Dict[float, Dict[str, Any]] = {}
        self.grid_levels: List[float] = []

        logger.info(
            f"Grid: {self.symbol} range=[{self.price_lower}, {self.price_upper}] "
            f"grids={self.num_grids} qty={self.quantity_per_grid}"
        )
        self._validate()
        self._calculate_grid_levels()

    def _validate(self) -> None:
        """Validate grid parameters."""
        validate_symbol(self.symbol)
        validate_price(self.price_lower)
        validate_price(self.price_upper)
        validate_quantity(self.quantity_per_grid)

        if self.price_upper <= self.price_lower:
            raise ValueError(
                f"Upper price ({self.price_upper}) must be > lower price ({self.price_lower})."
            )
        if self.num_grids < 2:
            raise ValueError(f"num_grids must be >= 2. Got {self.num_grids}.")

        logger.info("Grid parameters validated")

    def _calculate_grid_levels(self) -> None:
        """
        Calculate evenly spaced grid price levels.

        For N grids, we create N+1 price levels from lower to upper,
        giving us N intervals where orders can be placed.
        """
        step = (self.price_upper - self.price_lower) / self.num_grids
        self.grid_levels = [
            round(self.price_lower + i * step, 2)
            for i in range(self.num_grids + 1)
        ]
        logger.info(f"Grid levels: {self.grid_levels}")

    def _place_grid_orders(self, current_price: float) -> int:
        """
        Place initial grid orders: BUY below current price, SELL above.

        Args:
            current_price: Current market price to determine buy/sell split.

        Returns:
            Number of orders successfully placed.
        """
        orders_placed = 0

        for level in self.grid_levels:
            if level < current_price:
                # Place BUY limit order below current price
                side = "BUY"
            elif level > current_price:
                # Place SELL limit order above current price
                side = "SELL"
            else:
                # Skip levels at current price
                continue

            result = self.client.place_order(
                symbol=self.symbol, side=side, type="LIMIT",
                quantity=self.quantity_per_grid, price=level,
                timeInForce="GTC",
            )

            if result:
                order_id = result.get("orderId")
                self.active_orders[level] = {
                    "order_id": order_id, "side": side,
                    "price": level, "status": "NEW",
                }
                orders_placed += 1
                logger.info(f"Grid {side} @ ${level:,.2f} placed (ID: {order_id})")
                print(f"  ✅ {side:4s} @ ${level:,.2f} (ID: {order_id})")
            else:
                logger.error(f"Failed to place {side} @ ${level:,.2f}")
                print(f"  ❌ {side:4s} @ ${level:,.2f} — failed")

        return orders_placed

    def execute(self, monitor: bool = True) -> Dict[str, Any]:
        """
        Execute the grid strategy.

        Steps:
        1. Get current price
        2. Place buy orders below and sell orders above current price
        3. Optionally monitor and manage the grid

        Args:
            monitor: If True, start monitoring loop for filled orders.

        Returns:
            Summary of grid execution.
        """
        current_price = self.client.get_current_price(self.symbol)
        if not current_price:
            print("\n❌ Could not fetch current price. Aborting.")
            return {"error": "Could not fetch price"}

        print(f"\n{'='*60}")
        print(f"  Grid Trading Strategy")
        print(f"{'='*60}")
        print(f"  Symbol     : {self.symbol}")
        print(f"  Range      : ${self.price_lower:,.2f} — ${self.price_upper:,.2f}")
        print(f"  Grids      : {self.num_grids}")
        print(f"  Qty/Grid   : {self.quantity_per_grid}")
        print(f"  Cur. Price : ${current_price:,.2f}")
        grid_step = self.grid_levels[1] - self.grid_levels[0] if len(self.grid_levels) > 1 else 0
        print(f"  Grid Step  : ${grid_step:,.2f}")
        print(f"{'='*60}")
        print(f"\n  Placing grid orders...\n")

        orders_placed = self._place_grid_orders(current_price)

        print(f"\n  📊 {orders_placed} grid orders placed")
        logger.info(f"{orders_placed} grid orders placed")

        if monitor and orders_placed > 0:
            print(f"\n  🔄 Monitoring grid (polling every {POLL_INTERVAL}s)...")
            print(f"  Press Ctrl+C to stop.\n")
            return self._monitor_grid()
        else:
            return {"orders_placed": orders_placed, "grid_levels": self.grid_levels}

    def _monitor_grid(self) -> Dict[str, Any]:
        """
        Monitor the grid: when a buy fills, place a sell above it and vice versa.

        This is the core grid management loop that keeps the grid active.
        """
        fills = 0
        try:
            while True:
                for level, order_info in list(self.active_orders.items()):
                    order_id = order_info["order_id"]
                    status = self.client.get_order_status(self.symbol, order_id)

                    if not status:
                        continue

                    current_status = status.get("status", "")

                    if current_status == "FILLED":
                        fills += 1
                        filled_side = order_info["side"]
                        logger.info(f"Grid {filled_side} @ ${level:,.2f} FILLED!")
                        print(f"  🎯 {filled_side} @ ${level:,.2f} FILLED! (total fills: {fills})")

                        # Place the opposite order one grid step away
                        step = self.grid_levels[1] - self.grid_levels[0]
                        if filled_side == "BUY":
                            new_price = round(level + step, 2)
                            new_side = "SELL"
                        else:
                            new_price = round(level - step, 2)
                            new_side = "BUY"

                        # Only place if within grid bounds
                        if self.price_lower <= new_price <= self.price_upper:
                            new_result = self.client.place_order(
                                symbol=self.symbol, side=new_side, type="LIMIT",
                                quantity=self.quantity_per_grid, price=new_price,
                                timeInForce="GTC",
                            )
                            if new_result:
                                new_id = new_result.get("orderId")
                                self.active_orders[new_price] = {
                                    "order_id": new_id, "side": new_side,
                                    "price": new_price, "status": "NEW",
                                }
                                print(f"  ↔️  Placed {new_side} @ ${new_price:,.2f} (ID: {new_id})")

                        # Remove the filled order from tracking
                        del self.active_orders[level]

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Grid monitoring stopped by user")
            print(f"\n\n⚠️  Grid monitoring stopped. {fills} fills recorded.")
            print(f"   Active orders remain on Binance exchange.")
            return {"fills": fills, "status": "manual_stop"}


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for grid strategy."""
    parser = argparse.ArgumentParser(
        description="Execute Grid Trading on Binance Futures",
        epilog=(
            "Example:\n"
            "  python -m src.advanced.grid BTCUSDT 58000 62000 10 0.001\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", type=str, help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument("price_lower", type=float, help="Lower price bound")
    parser.add_argument("price_upper", type=float, help="Upper price bound")
    parser.add_argument("num_grids", type=int, help="Number of grid levels")
    parser.add_argument("quantity_per_grid", type=float, help="Qty per grid order")
    parser.add_argument("--no-monitor", action="store_true", help="Don't monitor after placing")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    print("="*60)
    print("  Binance Futures — Grid Trading Strategy")
    print("="*60)
    try:
        args = parse_arguments()
        grid = GridStrategy(args.symbol, args.price_lower, args.price_upper,
                            args.num_grids, args.quantity_per_grid)
        grid.execute(monitor=not args.no_monitor)
        sys.exit(0)
    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Grid strategy interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

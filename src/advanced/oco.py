"""
OCO (One-Cancels-Other) Order Module for Binance Futures Trading Bot.

An OCO order is a pair of orders linked together:
    1. Take-Profit order — closes position at a profit target
    2. Stop-Loss order   — closes position to limit losses

The key behavior: when ONE order fills, the OTHER is automatically cancelled.
This lets you set both a profit target and a safety net simultaneously.

Why OCO is important:
    Without OCO, if you place a take-profit and stop-loss separately,
    both could potentially execute (double execution), or you'd need
    to manually cancel one when the other fills.

Binance Futures Note:
    Binance Futures does NOT have a native OCO order type (unlike Spot).
    This module implements CUSTOM OCO logic:
    1. Place a TAKE_PROFIT_MARKET order (closes at profit target)
    2. Place a STOP_MARKET order (closes to limit losses)
    3. Monitor both orders in a polling loop
    4. When one fills, cancel the other

Example — Protecting a LONG position:
    You bought BTC at $60,000:
    - take_profit_price = $65,000 (sell for profit if price rises)
    - stop_loss_price   = $58,000 (sell to cut losses if price drops)
    - side              = SELL (closing a long position)

CLI Usage:
    python -m src.advanced.oco BTCUSDT SELL 0.001 65000 58000
    python -m src.advanced.oco ETHUSDT BUY 0.01 3500 4200

Module Usage:
    from src.advanced.oco import OCOOrder
    oco = OCOOrder("BTCUSDT", "SELL", 0.001, 65000, 58000)
    result = oco.execute()
"""

import sys
import time
import argparse
from typing import Any, Dict, List, Optional, Tuple

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

# How often to check order statuses (in seconds)
POLL_INTERVAL: int = 5

# Maximum time to monitor orders (in seconds) — 24 hours default
MAX_MONITOR_TIME: int = 86400


class OCOOrder:
    """
    Custom OCO (One-Cancels-Other) order for Binance Futures.

    Since Binance Futures doesn't support native OCO orders, this class
    implements the logic manually:
    1. Places two separate orders (take-profit + stop-loss)
    2. Monitors both orders by polling their status
    3. When one order fills, cancels the other

    Attributes:
        symbol:            Trading pair (e.g., "BTCUSDT").
        side:              "BUY" or "SELL" (the side of both orders).
        quantity:          Amount to trade.
        take_profit_price: Price target for taking profit.
        stop_loss_price:   Price level for cutting losses.
        client:            BinanceClient instance.
        tp_order_id:       Order ID of the take-profit order (set after placement).
        sl_order_id:       Order ID of the stop-loss order (set after placement).
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
    ) -> None:
        """
        Initialize an OCO order with validated parameters.

        Args:
            symbol:            Trading pair (e.g., "BTCUSDT").
            side:              "BUY" or "SELL".
            quantity:          Amount to trade.
            take_profit_price: Target price for profit.
            stop_loss_price:   Target price for stop-loss.

        Raises:
            ValueError: If parameters are invalid or prices are illogical.
        """
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.quantity = float(quantity)
        self.take_profit_price = float(take_profit_price)
        self.stop_loss_price = float(stop_loss_price)
        self.client = BinanceClient()
        self.tp_order_id: Optional[int] = None
        self.sl_order_id: Optional[int] = None

        logger.info(
            f"Initializing OCO: {self.side} {self.quantity} {self.symbol} "
            f"TP={self.take_profit_price} SL={self.stop_loss_price}"
        )
        self._validate()

    def _validate(self) -> None:
        """
        Validate parameters and price logic for the OCO pair.

        Price logic:
        - For SELL OCO (closing a long): TP > current price > SL
        - For BUY OCO (closing a short): SL > current price > TP
        """
        logger.info("Validating OCO order parameters...")
        validate_symbol(self.symbol)
        validate_side(self.side)
        validate_quantity(self.quantity)
        validate_price(self.take_profit_price)
        validate_price(self.stop_loss_price)

        if self.side == "SELL":
            # Closing a LONG position: take-profit above, stop-loss below
            if self.take_profit_price <= self.stop_loss_price:
                raise ValueError(
                    f"For SELL OCO (closing long): take_profit ({self.take_profit_price}) "
                    f"must be ABOVE stop_loss ({self.stop_loss_price}). "
                    f"TP is your profit target, SL limits your downside."
                )
        elif self.side == "BUY":
            # Closing a SHORT position: stop-loss above, take-profit below
            if self.stop_loss_price <= self.take_profit_price:
                raise ValueError(
                    f"For BUY OCO (closing short): stop_loss ({self.stop_loss_price}) "
                    f"must be ABOVE take_profit ({self.take_profit_price}). "
                    f"SL limits upside risk, TP is your downside profit target."
                )

        logger.info("All OCO parameters validated successfully")

    def _place_take_profit(self) -> Optional[Dict[str, Any]]:
        """
        Place the take-profit order (TAKE_PROFIT_MARKET).

        TAKE_PROFIT_MARKET triggers a market sell/buy when the price
        reaches the take-profit level, ensuring execution.
        """
        logger.info(
            f"Placing take-profit order: {self.side} @ ${self.take_profit_price:,.2f}"
        )
        return self.client.place_order(
            symbol=self.symbol,
            side=self.side,
            type="TAKE_PROFIT_MARKET",
            quantity=self.quantity,
            stopPrice=self.take_profit_price,
        )

    def _place_stop_loss(self) -> Optional[Dict[str, Any]]:
        """
        Place the stop-loss order (STOP_MARKET).

        STOP_MARKET triggers a market sell/buy when the price reaches
        the stop-loss level, ensuring execution to limit losses.
        """
        logger.info(
            f"Placing stop-loss order: {self.side} @ ${self.stop_loss_price:,.2f}"
        )
        return self.client.place_order(
            symbol=self.symbol,
            side=self.side,
            type="STOP_MARKET",
            quantity=self.quantity,
            stopPrice=self.stop_loss_price,
        )

    def execute(self, monitor: bool = True) -> Optional[Dict[str, Any]]:
        """
        Execute the OCO order pair and optionally monitor them.

        Steps:
        1. Place the take-profit order
        2. Place the stop-loss order
        3. If monitor=True, poll both orders until one fills
        4. Cancel the remaining order

        Args:
            monitor: If True, start a monitoring loop. If False, just place
                     both orders and return (manual monitoring required).

        Returns:
            A dictionary with the results of both orders.
        """
        try:
            current_price = self.client.get_current_price(self.symbol)
            if current_price:
                logger.info(f"Current {self.symbol} price: ${current_price:,.2f}")

            # Step 1: Place take-profit order
            tp_result = self._place_take_profit()
            if not tp_result:
                print("\n❌ Failed to place take-profit order. Aborting OCO.")
                return None

            self.tp_order_id = tp_result.get("orderId")
            print(f"\n✅ Take-Profit order placed (ID: {self.tp_order_id})")
            print(f"   Triggers at: ${self.take_profit_price:,.2f}")

            # Step 2: Place stop-loss order
            sl_result = self._place_stop_loss()
            if not sl_result:
                # If stop-loss fails, cancel the take-profit to avoid orphaned orders
                print("\n❌ Failed to place stop-loss order. Cancelling take-profit...")
                logger.warning("Stop-loss failed. Cancelling take-profit order.")
                self.client.cancel_order(self.symbol, self.tp_order_id)
                return None

            self.sl_order_id = sl_result.get("orderId")
            print(f"✅ Stop-Loss order placed (ID: {self.sl_order_id})")
            print(f"   Triggers at: ${self.stop_loss_price:,.2f}")

            logger.info(
                f"OCO pair placed: TP={self.tp_order_id}, SL={self.sl_order_id}"
            )

            print(f"\n{'=' * 60}")
            print(f"  OCO Order Summary")
            print(f"{'=' * 60}")
            print(f"  Symbol      : {self.symbol}")
            print(f"  Side        : {self.side}")
            print(f"  Quantity    : {self.quantity}")
            print(f"  Take-Profit : ${self.take_profit_price:,.2f} (order {self.tp_order_id})")
            print(f"  Stop-Loss   : ${self.stop_loss_price:,.2f} (order {self.sl_order_id})")
            print(f"{'=' * 60}")

            if monitor:
                print(f"\n  🔄 Monitoring orders (polling every {POLL_INTERVAL}s)...")
                print(f"  Press Ctrl+C to stop monitoring (orders remain active).\n")
                return self._monitor_orders()
            else:
                print(
                    f"\n  ℹ️  Orders placed. Monitor=False, so no automatic monitoring."
                )
                print(
                    f"  ⚠️  You must manually cancel the other order when one fills!"
                )
                return {"tp_order": tp_result, "sl_order": sl_result}

        except Exception as e:
            logger.error(f"Error executing OCO order: {e}", exc_info=True)
            print(f"\n❌ Error: {e}")
            return None

    def _monitor_orders(self) -> Optional[Dict[str, Any]]:
        """
        Monitor both OCO orders until one fills, then cancel the other.

        This polling loop checks both order statuses every POLL_INTERVAL
        seconds. When one order changes to FILLED, it cancels the other.

        Returns:
            A dictionary indicating which order filled and which was cancelled.
        """
        start_time = time.time()

        try:
            while (time.time() - start_time) < MAX_MONITOR_TIME:
                # Check take-profit status
                tp_status = self.client.get_order_status(
                    self.symbol, self.tp_order_id
                )
                sl_status = self.client.get_order_status(
                    self.symbol, self.sl_order_id
                )

                tp_state = tp_status.get("status", "UNKNOWN") if tp_status else "ERROR"
                sl_state = sl_status.get("status", "UNKNOWN") if sl_status else "ERROR"

                elapsed = int(time.time() - start_time)
                logger.debug(
                    f"OCO monitor [{elapsed}s]: TP={tp_state}, SL={sl_state}"
                )

                # Check if take-profit was filled
                if tp_state == "FILLED":
                    logger.info("Take-profit order FILLED! Cancelling stop-loss...")
                    print(f"\n🎯 Take-Profit FILLED at ${self.take_profit_price:,.2f}!")
                    self.client.cancel_order(self.symbol, self.sl_order_id)
                    print(f"   Stop-loss order (ID: {self.sl_order_id}) cancelled.")
                    return {"filled": "take_profit", "cancelled": "stop_loss"}

                # Check if stop-loss was filled
                if sl_state == "FILLED":
                    logger.info("Stop-loss order FILLED! Cancelling take-profit...")
                    print(f"\n🛑 Stop-Loss FILLED at ${self.stop_loss_price:,.2f}!")
                    self.client.cancel_order(self.symbol, self.tp_order_id)
                    print(f"   Take-profit order (ID: {self.tp_order_id}) cancelled.")
                    return {"filled": "stop_loss", "cancelled": "take_profit"}

                # Check for unexpected cancellations or errors
                if tp_state in ("CANCELED", "EXPIRED", "REJECTED"):
                    logger.warning(f"Take-profit order {tp_state}. Cancelling stop-loss...")
                    self.client.cancel_order(self.symbol, self.sl_order_id)
                    print(f"\n⚠️  Take-profit order {tp_state}. Stop-loss cancelled too.")
                    return {"error": f"TP order {tp_state}"}

                if sl_state in ("CANCELED", "EXPIRED", "REJECTED"):
                    logger.warning(f"Stop-loss order {sl_state}. Cancelling take-profit...")
                    self.client.cancel_order(self.symbol, self.tp_order_id)
                    print(f"\n⚠️  Stop-loss order {sl_state}. Take-profit cancelled too.")
                    return {"error": f"SL order {sl_state}"}

                # Both still active — wait before next poll
                time.sleep(POLL_INTERVAL)

            # Timeout reached
            logger.warning("OCO monitoring timed out")
            print(f"\n⚠️  Monitoring timed out after {MAX_MONITOR_TIME}s.")
            print(f"   Both orders remain active. Monitor manually or rerun.")
            return {"status": "timeout"}

        except KeyboardInterrupt:
            logger.info("OCO monitoring stopped by user (Ctrl+C)")
            print(f"\n⚠️  Monitoring stopped. Both orders remain active on Binance.")
            print(f"   TP Order ID: {self.tp_order_id}")
            print(f"   SL Order ID: {self.sl_order_id}")
            return {"status": "manual_stop"}


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for OCO order."""
    parser = argparse.ArgumentParser(
        description="Place an OCO (One-Cancels-Other) Order on Binance Futures",
        epilog=(
            "How OCO works:\n"
            "  1. A take-profit and stop-loss order are placed simultaneously\n"
            "  2. When one fills, the other is automatically cancelled\n"
            "  3. This protects your position from both sides\n"
            "\n"
            "Examples:\n"
            "  # Protect a LONG position (sell at profit or cut loss)\n"
            "  python -m src.advanced.oco BTCUSDT SELL 0.001 65000 58000\n"
            "\n"
            "  # Protect a SHORT position (buy at profit or cut loss)\n"
            "  python -m src.advanced.oco ETHUSDT BUY 0.01 3500 4200\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", type=str, help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument(
        "side", type=str, choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL"
    )
    parser.add_argument("quantity", type=float, help="Quantity to trade")
    parser.add_argument(
        "take_profit_price", type=float, help="Take-profit trigger price"
    )
    parser.add_argument(
        "stop_loss_price", type=float, help="Stop-loss trigger price"
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Place orders without monitoring (manual cancel required)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for CLI execution."""
    print("=" * 60)
    print("  Binance Futures — OCO Order (One-Cancels-Other)")
    print("=" * 60)

    try:
        args = parse_arguments()
        oco = OCOOrder(
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            take_profit_price=args.take_profit_price,
            stop_loss_price=args.stop_loss_price,
        )
        result = oco.execute(monitor=not args.no_monitor)
        sys.exit(0 if result else 1)

    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

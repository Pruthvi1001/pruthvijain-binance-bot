"""
TWAP (Time-Weighted Average Price) Strategy for Binance Futures.

TWAP splits a large order into smaller chunks executed at regular intervals
to minimize market impact and achieve a better average price.

How it works:
    1. chunk_size = total_quantity / num_chunks
    2. interval   = duration_seconds / num_chunks
    3. Execute market orders at each interval

CLI Usage:
    python -m src.advanced.twap BTCUSDT BUY 0.01 600 5
"""

import sys
import time
import argparse
from typing import Any, Dict, List, Optional

from src.client import BinanceClient
from src.logger_setup import setup_logger
from src.validators import validate_symbol, validate_side, validate_quantity

logger = setup_logger(__name__)


class TWAPStrategy:
    """
    Time-Weighted Average Price execution strategy.

    Splits a large order into smaller chunks executed at regular time
    intervals to minimize market impact.

    Attributes:
        symbol:           Trading pair (e.g., "BTCUSDT").
        side:             "BUY" or "SELL".
        total_quantity:   Total amount to trade.
        duration_seconds: Total time window for execution.
        num_chunks:       Number of chunks to split the order into.
        chunk_size:       Quantity per individual order.
        interval:         Time between each order (seconds).
    """

    def __init__(
        self, symbol: str, side: str, total_quantity: float,
        duration_seconds: int, num_chunks: int,
    ) -> None:
        """Initialize TWAP strategy with validated parameters."""
        self.symbol = symbol.upper()
        self.side = side.upper()
        self.total_quantity = float(total_quantity)
        self.duration_seconds = int(duration_seconds)
        self.num_chunks = int(num_chunks)
        self.client = BinanceClient()

        self.chunk_size = self.total_quantity / self.num_chunks
        self.interval = self.duration_seconds / self.num_chunks

        logger.info(
            f"TWAP: {self.side} {self.total_quantity} {self.symbol} "
            f"over {self.duration_seconds}s in {self.num_chunks} chunks"
        )
        self._validate()

    def _validate(self) -> None:
        """Validate all strategy parameters."""
        validate_symbol(self.symbol)
        validate_side(self.side)
        validate_quantity(self.total_quantity)
        if self.num_chunks <= 0:
            raise ValueError(f"num_chunks must be > 0. Got {self.num_chunks}.")
        if self.duration_seconds <= 0:
            raise ValueError(f"duration must be > 0s. Got {self.duration_seconds}.")
        if self.chunk_size <= 0:
            raise ValueError(f"Chunk size ({self.chunk_size}) too small.")
        if self.interval < 1:
            logger.warning(f"Interval ({self.interval:.1f}s) very short — may hit rate limits.")
        logger.info("TWAP parameters validated")

    def execute(self) -> Dict[str, Any]:
        """
        Execute the TWAP strategy, placing market orders at regular intervals.

        Returns:
            Summary dict with total_executed, average_price, chunk_results, etc.
        """
        print(f"\n{'='*60}")
        print(f"  TWAP Execution Plan")
        print(f"{'='*60}")
        print(f"  Symbol     : {self.symbol}")
        print(f"  Side       : {self.side}")
        print(f"  Total Qty  : {self.total_quantity}")
        print(f"  Chunks     : {self.num_chunks} x {self.chunk_size}")
        print(f"  Interval   : {self.interval:.1f}s")
        print(f"  Duration   : {self.duration_seconds}s ({self.duration_seconds/60:.1f}min)")
        print(f"{'='*60}\n")

        chunk_results: List[Dict[str, Any]] = []
        total_executed = 0.0
        total_cost = 0.0
        chunks_completed = 0

        for i in range(self.num_chunks):
            chunk_num = i + 1
            try:
                progress = (chunk_num / self.num_chunks) * 100
                logger.info(f"TWAP chunk {chunk_num}/{self.num_chunks} ({progress:.0f}%)")
                print(f"  [{chunk_num}/{self.num_chunks}] {self.side} {self.chunk_size} {self.symbol}...", end=" ")

                result = self.client.place_order(
                    symbol=self.symbol, side=self.side,
                    type="MARKET", quantity=self.chunk_size,
                )

                if result:
                    filled_qty = float(result.get("executedQty", 0))
                    avg_price = float(result.get("avgPrice", 0))
                    total_executed += filled_qty
                    total_cost += filled_qty * avg_price
                    chunks_completed += 1
                    running_avg = total_cost / total_executed if total_executed > 0 else 0
                    chunk_results.append({
                        "chunk": chunk_num, "order_id": result.get("orderId"),
                        "filled_qty": filled_qty, "avg_price": avg_price,
                        "status": result.get("status"),
                    })
                    print(f"✅ {filled_qty} @ ${avg_price:,.2f} (avg: ${running_avg:,.2f})")
                else:
                    print(f"❌ Failed (continuing)")
                    chunk_results.append({"chunk": chunk_num, "status": "FAILED"})

            except Exception as e:
                logger.error(f"Chunk {chunk_num} error: {e}", exc_info=True)
                print(f"❌ Error: {e}")
                chunk_results.append({"chunk": chunk_num, "status": "ERROR", "error": str(e)})

            if chunk_num < self.num_chunks:
                print(f"  ⏳ Waiting {self.interval:.1f}s...")
                time.sleep(self.interval)

        average_price = total_cost / total_executed if total_executed > 0 else 0
        print(f"\n{'='*60}")
        print(f"  TWAP Complete!")
        print(f"  Chunks: {chunks_completed}/{self.num_chunks}")
        print(f"  Executed: {total_executed}")
        print(f"  Avg Price: ${average_price:,.2f}")
        print(f"  Total Cost: ${total_cost:,.2f}")
        print(f"{'='*60}")

        logger.info(f"TWAP done: {chunks_completed}/{self.num_chunks}, avg={average_price:.2f}")
        return {
            "total_executed": total_executed, "total_chunks_completed": chunks_completed,
            "average_price": average_price, "total_cost": total_cost,
            "chunk_results": chunk_results,
        }


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for TWAP."""
    parser = argparse.ArgumentParser(
        description="Execute TWAP Strategy on Binance Futures",
        epilog="Example: python -m src.advanced.twap BTCUSDT BUY 0.01 600 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("symbol", type=str, help="Trading pair (e.g., BTCUSDT)")
    parser.add_argument("side", type=str, choices=["BUY","SELL","buy","sell"], help="BUY or SELL")
    parser.add_argument("total_quantity", type=float, help="Total quantity")
    parser.add_argument("duration_seconds", type=int, help="Duration in seconds")
    parser.add_argument("num_chunks", type=int, help="Number of chunks")
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    print("="*60)
    print("  Binance Futures — TWAP Strategy")
    print("="*60)
    try:
        args = parse_arguments()
        twap = TWAPStrategy(args.symbol, args.side, args.total_quantity,
                            args.duration_seconds, args.num_chunks)
        result = twap.execute()
        sys.exit(0 if result.get("total_chunks_completed", 0) > 0 else 1)
    except ValueError as e:
        print(f"\n❌ Validation Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  TWAP interrupted. Some chunks may have executed.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

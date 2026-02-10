"""
Historical Trade Data Analysis for Binance Futures Trading Bot.

This module loads and analyzes the historical trading data CSV file,
providing insights into past trading performance including:

    - Total trades and volume
    - Per-coin breakdown (PnL, win rate, avg trade size)
    - Realized PnL analysis
    - Fee summary
    - Trade direction analysis (Buy/Sell split)

The data comes from a DeFi perpetuals exchange and mirrors the kind of
trade history you'd see on Binance Futures. Each row is a single fill
(a large order can have many fills).

CSV Columns:
    Account, Coin, Execution Price, Size Tokens, Size USD, Side,
    Timestamp IST, Start Position, Direction, Closed PnL,
    Transaction Hash, Order ID, Crossed, Fee, Trade ID, Timestamp

CLI Usage:
    python -m src.analysis.historical_analysis [--coin COINNAME]
    python -m src.analysis.historical_analysis --coin AIXBT
    python -m src.analysis.historical_analysis --top 5
"""

import os
import csv
import argparse
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.logger_setup import setup_logger

logger = setup_logger(__name__)

# Default CSV path
DATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CSV = os.path.join(DATA_DIR, "historical_data.csv")


def load_historical_data(csv_path: str = DEFAULT_CSV) -> List[Dict[str, Any]]:
    """
    Load historical trade data from CSV.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of trade dictionaries with parsed numeric fields.
    """
    if not os.path.exists(csv_path):
        logger.error(f"Historical data file not found: {csv_path}")
        print(f"\n❌ File not found: {csv_path}")
        return []

    trades: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trade = {
                    "coin": row.get("Coin", "").strip(),
                    "price": float(row.get("Execution Price", 0)),
                    "size_tokens": float(row.get("Size Tokens", 0)),
                    "size_usd": float(row.get("Size USD", 0)),
                    "side": row.get("Side", "").strip().upper(),
                    "timestamp": row.get("Timestamp IST", "").strip(),
                    "direction": row.get("Direction", "").strip(),
                    "closed_pnl": float(row.get("Closed PnL", 0)),
                    "fee": float(row.get("Fee", 0)),
                    "order_id": row.get("Order ID", "").strip(),
                }
                trades.append(trade)
            except (ValueError, TypeError):
                continue  # skip malformed rows

    logger.info(f"Loaded {len(trades)} trades from {csv_path}")
    return trades


def analyze_overall(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute overall portfolio statistics."""
    total_volume = sum(t["size_usd"] for t in trades)
    total_pnl = sum(t["closed_pnl"] for t in trades)
    total_fees = sum(t["fee"] for t in trades)
    buy_count = sum(1 for t in trades if t["side"] == "BUY")
    sell_count = sum(1 for t in trades if t["side"] == "SELL")
    unique_coins = len(set(t["coin"] for t in trades))

    return {
        "total_trades": len(trades),
        "unique_coins": unique_coins,
        "total_volume_usd": total_volume,
        "total_realized_pnl": total_pnl,
        "total_fees": total_fees,
        "net_pnl": total_pnl - total_fees,
        "buy_trades": buy_count,
        "sell_trades": sell_count,
    }


def analyze_by_coin(trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Compute per-coin statistics."""
    coin_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in trades:
        coin_data[t["coin"]].append(t)

    results = {}
    for coin, coin_trades in coin_data.items():
        volume = sum(t["size_usd"] for t in coin_trades)
        pnl = sum(t["closed_pnl"] for t in coin_trades)
        fees = sum(t["fee"] for t in coin_trades)
        profitable_trades = sum(1 for t in coin_trades if t["closed_pnl"] > 0)
        closing_trades = sum(1 for t in coin_trades if t["closed_pnl"] != 0)
        win_rate = (profitable_trades / closing_trades * 100) if closing_trades > 0 else 0

        results[coin] = {
            "trades": len(coin_trades),
            "volume_usd": volume,
            "realized_pnl": pnl,
            "fees": fees,
            "net_pnl": pnl - fees,
            "win_rate": win_rate,
            "avg_trade_usd": volume / len(coin_trades) if coin_trades else 0,
        }

    return results


def print_report(trades: List[Dict[str, Any]], coin_filter: Optional[str] = None,
                 top_n: int = 10) -> None:
    """Print a formatted analysis report."""
    if coin_filter:
        trades = [t for t in trades if t["coin"] == coin_filter.upper() or t["coin"] == coin_filter]
        if not trades:
            print(f"\n❌ No trades found for coin: {coin_filter}")
            return

    overall = analyze_overall(trades)
    coin_stats = analyze_by_coin(trades)

    print(f"\n{'='*65}")
    print(f"  📊 Historical Trade Analysis Report")
    print(f"{'='*65}")

    if coin_filter:
        print(f"  Filter        : {coin_filter}")

    print(f"  Total Trades   : {overall['total_trades']:,}")
    print(f"  Unique Coins   : {overall['unique_coins']}")
    print(f"  Total Volume   : ${overall['total_volume_usd']:,.2f}")
    print(f"  Realized PnL   : ${overall['total_realized_pnl']:,.2f}")
    print(f"  Total Fees     : ${overall['total_fees']:,.2f}")
    pnl_color = "🟢" if overall['net_pnl'] >= 0 else "🔴"
    print(f"  Net PnL        : {pnl_color} ${overall['net_pnl']:,.2f}")
    print(f"  Buy/Sell Split : {overall['buy_trades']} / {overall['sell_trades']}")

    # Per-coin breakdown (top N by volume)
    sorted_coins = sorted(coin_stats.items(), key=lambda x: x[1]["volume_usd"], reverse=True)
    display_coins = sorted_coins[:top_n]

    print(f"\n{'─'*65}")
    print(f"  Top {min(top_n, len(display_coins))} Coins by Volume")
    print(f"{'─'*65}")
    print(f"  {'Coin':<10} {'Trades':>8} {'Volume':>14} {'Net PnL':>14} {'Win%':>7}")
    print(f"  {'─'*10} {'─'*8} {'─'*14} {'─'*14} {'─'*7}")

    for coin, stats in display_coins:
        pnl_str = f"${stats['net_pnl']:,.2f}"
        print(
            f"  {coin:<10} {stats['trades']:>8,} "
            f"${stats['volume_usd']:>12,.2f} "
            f"{pnl_str:>14} "
            f"{stats['win_rate']:>6.1f}%"
        )

    print(f"{'='*65}\n")


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze historical trading data",
        epilog="Examples:\n  python -m src.analysis.historical_analysis\n"
               "  python -m src.analysis.historical_analysis --coin AIXBT\n"
               "  python -m src.analysis.historical_analysis --top 5\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", type=str, default=DEFAULT_CSV, help="Path to CSV file")
    parser.add_argument("--coin", type=str, default=None, help="Filter by coin name")
    parser.add_argument("--top", type=int, default=10, help="Show top N coins (default: 10)")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    print("="*65)
    print("  Binance Futures — Historical Data Analysis")
    print("="*65)
    trades = load_historical_data(args.file)
    if trades:
        print_report(trades, coin_filter=args.coin, top_n=args.top)


if __name__ == "__main__":
    main()

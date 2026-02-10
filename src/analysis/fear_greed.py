"""
Fear & Greed Index Analysis for Binance Futures Trading Bot.

The Crypto Fear & Greed Index measures market sentiment on a scale of 0-100:

    0-24  = Extreme Fear   → Investors are very worried (potential buying opportunity)
    25-49 = Fear           → Market is cautious
    50-74 = Greed          → Market is optimistic
    75-100 = Extreme Greed → Market is euphoric (potential selling opportunity)

Contrarian Strategy:
    "Be fearful when others are greedy, and greedy when others are fearful" — Buffett

    - Buy signals in Extreme Fear (index < 25) → market may be oversold
    - Sell signals in Extreme Greed (index > 75) → market may be overbought

This module:
    1. Loads fear_greed_index.csv (daily data from 2018-present)
    2. Shows current/latest sentiment reading
    3. Provides historical sentiment statistics
    4. Generates buy/sell signals based on sentiment thresholds
    5. Can filter analysis by date range

CSV Columns: timestamp, value, classification, date

CLI Usage:
    python -m src.analysis.fear_greed
    python -m src.analysis.fear_greed --latest 30
    python -m src.analysis.fear_greed --signal
"""

import os
import csv
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.logger_setup import setup_logger

logger = setup_logger(__name__)

# Default CSV path
DATA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CSV = os.path.join(DATA_DIR, "fear_greed_index.csv")

# Sentiment thresholds
EXTREME_FEAR_THRESHOLD = 25
FEAR_THRESHOLD = 45
GREED_THRESHOLD = 55
EXTREME_GREED_THRESHOLD = 75


def load_fear_greed_data(csv_path: str = DEFAULT_CSV) -> List[Dict[str, Any]]:
    """
    Load Fear & Greed Index data from CSV.

    Returns:
        List of daily sentiment readings, sorted by date ascending.
    """
    if not os.path.exists(csv_path):
        logger.error(f"Fear & Greed data file not found: {csv_path}")
        print(f"\n❌ File not found: {csv_path}")
        return []

    data: List[Dict[str, Any]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                entry = {
                    "date": row.get("date", "").strip(),
                    "value": int(row.get("value", 0)),
                    "classification": row.get("classification", "").strip(),
                }
                data.append(entry)
            except (ValueError, TypeError):
                continue

    # Sort by date ascending
    data.sort(key=lambda x: x["date"])
    logger.info(f"Loaded {len(data)} Fear & Greed entries from {csv_path}")
    return data


def get_sentiment_label(value: int) -> str:
    """Map a 0-100 value to a sentiment label with emoji."""
    if value <= 10:
        return "😱 Extreme Fear"
    elif value < EXTREME_FEAR_THRESHOLD:
        return "😰 Extreme Fear"
    elif value < FEAR_THRESHOLD:
        return "😟 Fear"
    elif value < GREED_THRESHOLD:
        return "😐 Neutral"
    elif value < EXTREME_GREED_THRESHOLD:
        return "😊 Greed"
    else:
        return "🤑 Extreme Greed"


def get_signal(value: int) -> str:
    """Generate a contrarian trading signal based on sentiment."""
    if value < EXTREME_FEAR_THRESHOLD:
        return "🟢 BUY SIGNAL — Market is in Extreme Fear (potential bottom)"
    elif value < FEAR_THRESHOLD:
        return "🔵 ACCUMULATE — Market is fearful (cautious buying)"
    elif value < GREED_THRESHOLD:
        return "⚪ NEUTRAL — No clear sentiment-based signal"
    elif value < EXTREME_GREED_THRESHOLD:
        return "🟡 CAUTION — Market is greedy (consider taking profits)"
    else:
        return "🔴 SELL SIGNAL — Market is in Extreme Greed (potential top)"


def analyze_sentiment(data: List[Dict[str, Any]], latest_n: int = 0) -> Dict[str, Any]:
    """
    Compute sentiment statistics.

    Args:
        data:     Full dataset.
        latest_n: If > 0, only analyze the most recent N entries.

    Returns:
        Dictionary with statistical summary.
    """
    if latest_n > 0:
        analysis_data = data[-latest_n:]
    else:
        analysis_data = data

    if not analysis_data:
        return {}

    values = [d["value"] for d in analysis_data]
    avg = sum(values) / len(values)

    # Classification distribution
    distribution: Dict[str, int] = {}
    for d in analysis_data:
        cls = d["classification"]
        distribution[cls] = distribution.get(cls, 0) + 1

    # Extreme days
    extreme_fear_days = sum(1 for v in values if v < EXTREME_FEAR_THRESHOLD)
    extreme_greed_days = sum(1 for v in values if v >= EXTREME_GREED_THRESHOLD)

    return {
        "period_start": analysis_data[0]["date"],
        "period_end": analysis_data[-1]["date"],
        "total_days": len(analysis_data),
        "avg_value": avg,
        "min_value": min(values),
        "max_value": max(values),
        "latest_value": analysis_data[-1]["value"],
        "latest_class": analysis_data[-1]["classification"],
        "latest_date": analysis_data[-1]["date"],
        "extreme_fear_days": extreme_fear_days,
        "extreme_greed_days": extreme_greed_days,
        "distribution": distribution,
    }


def print_report(data: List[Dict[str, Any]], latest_n: int = 0,
                 show_signal: bool = False) -> None:
    """Print a formatted Fear & Greed analysis report."""
    if not data:
        return

    stats = analyze_sentiment(data, latest_n)
    if not stats:
        print("No data to analyze.")
        return

    latest_val = stats["latest_value"]
    sentiment = get_sentiment_label(latest_val)

    print(f"\n{'='*60}")
    print(f"  🌡️  Crypto Fear & Greed Index Report")
    print(f"{'='*60}")
    print(f"  Latest Reading : {latest_val}/100 — {sentiment}")
    print(f"  Date           : {stats['latest_date']}")
    print(f"  Period         : {stats['period_start']} → {stats['period_end']}")
    print(f"  Total Days     : {stats['total_days']:,}")

    print(f"\n{'─'*60}")
    print(f"  Statistics")
    print(f"{'─'*60}")
    print(f"  Average        : {stats['avg_value']:.1f}/100")
    print(f"  Min            : {stats['min_value']}/100")
    print(f"  Max            : {stats['max_value']}/100")
    print(f"  Extreme Fear   : {stats['extreme_fear_days']} days ({stats['extreme_fear_days']/stats['total_days']*100:.1f}%)")
    print(f"  Extreme Greed  : {stats['extreme_greed_days']} days ({stats['extreme_greed_days']/stats['total_days']*100:.1f}%)")

    # Distribution
    print(f"\n{'─'*60}")
    print(f"  Sentiment Distribution")
    print(f"{'─'*60}")
    order = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
    for cls in order:
        count = stats["distribution"].get(cls, 0)
        pct = count / stats["total_days"] * 100 if stats["total_days"] > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {cls:<14} {count:>5} ({pct:>5.1f}%) {bar}")

    # Trading signal
    if show_signal:
        signal = get_signal(latest_val)
        print(f"\n{'─'*60}")
        print(f"  Contrarian Trading Signal")
        print(f"{'─'*60}")
        print(f"  {signal}")
        print()
        print(f"  Strategy: \"Be fearful when others are greedy,")
        print(f"             and greedy when others are fearful.\"")

    # Recent trend (last 7 values)
    recent = data[-7:] if len(data) >= 7 else data
    print(f"\n{'─'*60}")
    print(f"  Recent 7-Day Trend")
    print(f"{'─'*60}")
    for d in recent:
        bar = "▓" * (d["value"] // 5)
        print(f"  {d['date']}  {d['value']:>3}/100  {bar}  {d['classification']}")

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crypto Fear & Greed Index Analysis",
        epilog="Examples:\n"
               "  python -m src.analysis.fear_greed\n"
               "  python -m src.analysis.fear_greed --latest 30\n"
               "  python -m src.analysis.fear_greed --signal\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", type=str, default=DEFAULT_CSV, help="Path to CSV file")
    parser.add_argument("--latest", type=int, default=0, help="Analyze only the latest N days")
    parser.add_argument("--signal", action="store_true", help="Show contrarian trading signal")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    print("="*60)
    print("  Binance Futures — Fear & Greed Index Analysis")
    print("="*60)
    data = load_fear_greed_data(args.file)
    if data:
        print_report(data, latest_n=args.latest, show_signal=args.signal)


if __name__ == "__main__":
    main()

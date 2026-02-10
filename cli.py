"""
Unified CLI Entry Point for Binance Futures Trading Bot.

This module provides a single, interactive command-line interface for
placing all supported order types on Binance Futures Testnet.

Two modes:
  1. Direct mode:  python cli.py market BTCUSDT BUY 0.002
  2. Interactive:   python cli.py  (launches menu)

Supports:
  - Market Orders
  - Limit Orders
  - Stop-Limit Orders
  - OCO Orders (One-Cancels-the-Other)
  - TWAP Strategy (Time-Weighted Average Price)
  - Grid Trading Strategy

Enhanced UX:
  - Colored terminal output
  - Interactive prompts with validation
  - Order confirmation before execution
  - Detailed order response display
"""

import argparse
import sys
import os

from src.client import BinanceClient
from src.validators import validate_symbol, validate_side, validate_quantity, validate_price
from src.logger_setup import setup_logger

logger = setup_logger("cli")

# ─── ANSI Colors ──────────────────────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_BLUE = "\033[44m"
BG_GREEN = "\033[42m"
BG_RED = "\033[41m"


def banner():
    """Print the application banner."""
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════╗
║          🚀  Binance Futures Trading Bot  🚀                ║
║          ── USDT-M Futures · Testnet ──                     ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")


def print_success(msg):
    print(f"  {GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"  {RED}❌ {msg}{RESET}")


def print_warn(msg):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def print_info(msg):
    print(f"  {CYAN}ℹ️  {msg}{RESET}")


def print_header(title):
    width = 60
    print(f"\n{BLUE}{BOLD}{'═' * width}{RESET}")
    print(f"{BLUE}{BOLD}  {title}{RESET}")
    print(f"{BLUE}{BOLD}{'═' * width}{RESET}")


def print_order_response(order: dict):
    """
    Print a detailed, formatted order response.

    Displays: orderId, symbol, side, type, status, origQty,
              executedQty, avgPrice, price, stopPrice.
    """
    if not order:
        print_error("No order response received.")
        return

    print(f"\n  {GREEN}{BOLD}┌──────────────────────────────────────────────┐{RESET}")
    print(f"  {GREEN}{BOLD}│         ORDER EXECUTED SUCCESSFULLY          │{RESET}")
    print(f"  {GREEN}{BOLD}└──────────────────────────────────────────────┘{RESET}\n")

    fields = [
        ("Order ID", order.get("orderId", "N/A")),
        ("Symbol", order.get("symbol", "N/A")),
        ("Side", order.get("side", "N/A")),
        ("Type", order.get("type", "N/A")),
        ("Status", order.get("status", "N/A")),
        ("Quantity", order.get("origQty", "N/A")),
        ("Executed Qty", order.get("executedQty", "0")),
        ("Avg Price", f"${float(order.get('avgPrice', 0)):,.2f}" if order.get("avgPrice") else "N/A"),
        ("Price", f"${float(order.get('price', 0)):,.2f}" if float(order.get("price", 0)) > 0 else "Market"),
    ]

    if order.get("stopPrice") and float(order.get("stopPrice", 0)) > 0:
        fields.append(("Stop Price", f"${float(order['stopPrice']):,.2f}"))

    if order.get("timeInForce"):
        fields.append(("Time In Force", order["timeInForce"]))

    for label, value in fields:
        side = order.get("side", "")
        if label == "Side":
            color = GREEN if value == "BUY" else RED
            print(f"  {DIM}{label:<16}{RESET} {color}{BOLD}{value}{RESET}")
        elif label == "Status":
            color = GREEN if value in ("NEW", "FILLED", "PARTIALLY_FILLED") else YELLOW
            print(f"  {DIM}{label:<16}{RESET} {color}{BOLD}{value}{RESET}")
        else:
            print(f"  {DIM}{label:<16}{RESET} {WHITE}{BOLD}{value}{RESET}")

    print()


def prompt_input(label, default=None, validator=None, cast=None):
    """Prompt user for input with optional validation and casting."""
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"  {CYAN}›{RESET} {label}{suffix}: ").strip()

        if not raw and default:
            raw = str(default)

        if not raw:
            print_warn("Input required.")
            continue

        if cast:
            try:
                raw = cast(raw)
            except (ValueError, TypeError):
                print_warn(f"Invalid input. Expected {cast.__name__}.")
                continue

        if validator:
            try:
                validator(raw)
            except ValueError as e:
                print_warn(str(e))
                continue

        return raw


def confirm_order(details: dict) -> bool:
    """Show order summary and ask for confirmation."""
    print(f"\n  {YELLOW}{BOLD}┌──────────────────────────────────────────────┐{RESET}")
    print(f"  {YELLOW}{BOLD}│           ORDER CONFIRMATION                 │{RESET}")
    print(f"  {YELLOW}{BOLD}└──────────────────────────────────────────────┘{RESET}\n")

    for label, value in details.items():
        print(f"  {DIM}{label:<16}{RESET} {WHITE}{BOLD}{value}{RESET}")

    print()
    answer = input(f"  {YELLOW}› Confirm and place this order? (y/n): {RESET}").strip().lower()
    return answer in ("y", "yes")


# ─── Order Handlers ───────────────────────────────────────────────────────────

def handle_market_order(client, symbol, side, quantity):
    """Place a market order."""
    print_header("Market Order")

    price_info = client.get_current_price(symbol)
    if price_info:
        print_info(f"Current {symbol} price: ${price_info:,.2f}")

    confirmed = confirm_order({
        "Type": "MARKET",
        "Symbol": symbol,
        "Side": side,
        "Quantity": quantity,
    })

    if not confirmed:
        print_warn("Order cancelled by user.")
        return

    logger.info(f"Placing MARKET order: {side} {quantity} {symbol}")
    order = client.place_order(
        symbol=symbol,
        side=side,
        type="MARKET",
        quantity=quantity,
    )

    if order:
        print_order_response(order)
        logger.info(f"Market order response: {order}")
    else:
        print_error("Order failed. Check bot.log for details.")


def handle_limit_order(client, symbol, side, quantity, price):
    """Place a limit order."""
    print_header("Limit Order")

    price_info = client.get_current_price(symbol)
    if price_info:
        print_info(f"Current {symbol} price: ${price_info:,.2f}")

    confirmed = confirm_order({
        "Type": "LIMIT (GTC)",
        "Symbol": symbol,
        "Side": side,
        "Quantity": quantity,
        "Price": f"${price:,.2f}",
    })

    if not confirmed:
        print_warn("Order cancelled by user.")
        return

    logger.info(f"Placing LIMIT order: {side} {quantity} {symbol} @ ${price}")
    order = client.place_order(
        symbol=symbol,
        side=side,
        type="LIMIT",
        quantity=quantity,
        price=price,
        timeInForce="GTC",
    )

    if order:
        print_order_response(order)
        logger.info(f"Limit order response: {order}")
    else:
        print_error("Order failed. Check bot.log for details.")


def handle_stop_limit_order(client, symbol, side, quantity, stop_price, limit_price):
    """Place a stop-limit order."""
    print_header("Stop-Limit Order")

    price_info = client.get_current_price(symbol)
    if price_info:
        print_info(f"Current {symbol} price: ${price_info:,.2f}")

    confirmed = confirm_order({
        "Type": "STOP-LIMIT",
        "Symbol": symbol,
        "Side": side,
        "Quantity": quantity,
        "Stop Price": f"${stop_price:,.2f}",
        "Limit Price": f"${limit_price:,.2f}",
    })

    if not confirmed:
        print_warn("Order cancelled by user.")
        return

    logger.info(f"Placing STOP-LIMIT: {side} {quantity} {symbol} stop={stop_price} limit={limit_price}")
    order = client.place_order(
        symbol=symbol,
        side=side,
        type="STOP",
        quantity=quantity,
        price=limit_price,
        stopPrice=stop_price,
        timeInForce="GTC",
    )

    if order:
        print_order_response(order)
    else:
        print_error("Order failed. Check bot.log for details.")


# ─── Interactive Menu ─────────────────────────────────────────────────────────

def interactive_menu():
    """Launch the interactive trading menu."""
    banner()

    try:
        client = BinanceClient()
        print_success("Connected to Binance Futures Testnet")
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        return

    # Show account info
    try:
        price = client.get_current_price("BTCUSDT")
        balance = client.get_account_balance()
        if price:
            print_info(f"BTCUSDT: ${price:,.2f}")
        if balance:
            print_info(f"USDT Balance: {balance.get('availableBalance', 'N/A')}")
    except Exception:
        pass

    while True:
        print(f"""
{BOLD}  ┌─────────────────────────────────────────┐
  │          SELECT ORDER TYPE               │
  ├─────────────────────────────────────────┤{RESET}
  │  {GREEN}1{RESET}  │  Market Order                     │
  │  {GREEN}2{RESET}  │  Limit Order                      │
  │  {GREEN}3{RESET}  │  Stop-Limit Order         {MAGENTA}[Bonus]{RESET} │
  │  {GREEN}4{RESET}  │  OCO Order                {MAGENTA}[Bonus]{RESET} │
  │  {GREEN}5{RESET}  │  TWAP Strategy            {MAGENTA}[Bonus]{RESET} │
  │  {GREEN}6{RESET}  │  Grid Trading             {MAGENTA}[Bonus]{RESET} │
  │  {DIM}─────┼───────────────────────────────────{RESET} │
  │  {CYAN}7{RESET}  │  Historical Data Analysis          │
  │  {CYAN}8{RESET}  │  Fear & Greed Index                │
  │  {DIM}─────┼───────────────────────────────────{RESET} │
  │  {YELLOW}9{RESET}  │  View Account / Positions          │
  │  {RED}0{RESET}  │  Exit                              │
  └─────┴───────────────────────────────────┘""")

        choice = input(f"\n  {CYAN}› Choose [0-9]: {RESET}").strip()

        if choice == "0":
            print(f"\n  {DIM}Goodbye! 👋{RESET}\n")
            break

        elif choice == "1":
            # Market Order
            symbol = prompt_input("Symbol (e.g., BTCUSDT)", "BTCUSDT", validate_symbol, str).upper()
            side = prompt_input("Side (BUY/SELL)", "BUY", validate_side, str).upper()
            quantity = prompt_input("Quantity", None, validate_quantity, float)
            handle_market_order(client, symbol, side, quantity)

        elif choice == "2":
            # Limit Order
            symbol = prompt_input("Symbol (e.g., BTCUSDT)", "BTCUSDT", validate_symbol, str).upper()
            side = prompt_input("Side (BUY/SELL)", "BUY", validate_side, str).upper()
            quantity = prompt_input("Quantity", None, validate_quantity, float)
            price = prompt_input("Limit Price ($)", None, validate_price, float)
            handle_limit_order(client, symbol, side, quantity, price)

        elif choice == "3":
            # Stop-Limit
            symbol = prompt_input("Symbol", "BTCUSDT", validate_symbol, str).upper()
            side = prompt_input("Side (BUY/SELL)", "SELL", validate_side, str).upper()
            quantity = prompt_input("Quantity", None, validate_quantity, float)
            stop_price = prompt_input("Stop Price ($)", None, validate_price, float)
            limit_price = prompt_input("Limit Price ($)", None, validate_price, float)
            handle_stop_limit_order(client, symbol, side, quantity, stop_price, limit_price)

        elif choice == "4":
            # OCO
            print_header("OCO Order")
            print_info("Launching OCO module...")
            symbol = str(prompt_input("Symbol", "BTCUSDT", validate_symbol, str)).upper()
            side = str(prompt_input("Side (BUY/SELL)", "SELL", validate_side, str)).upper()
            quantity = float(prompt_input("Quantity", None, validate_quantity, float))
            tp_price = float(prompt_input("Take-Profit Price ($)", None, validate_price, float))
            sl_price = float(prompt_input("Stop-Loss Price ($)", None, validate_price, float))

            confirmed = confirm_order({
                "Type": "OCO (One-Cancels-Other)",
                "Symbol": symbol,
                "Side": side,
                "Quantity": quantity,
                "Take Profit": f"${tp_price:,.2f}",
                "Stop Loss": f"${sl_price:,.2f}",
            })
            if confirmed:
                from src.advanced.oco import OCOOrder
                oco = OCOOrder(symbol, side, quantity, tp_price, sl_price)
                oco.execute()
            else:
                print_warn("Order cancelled.")

        elif choice == "5":
            # TWAP
            print_header("TWAP Strategy")
            symbol = str(prompt_input("Symbol", "BTCUSDT", validate_symbol, str)).upper()
            side = str(prompt_input("Side (BUY/SELL)", "BUY", validate_side, str)).upper()
            quantity = float(prompt_input("Total Quantity", None, validate_quantity, float))
            duration = int(prompt_input("Duration (seconds)", "600", None, int))
            chunks = int(prompt_input("Number of Chunks", "5", None, int))

            confirmed = confirm_order({
                "Type": "TWAP",
                "Symbol": symbol,
                "Side": side,
                "Total Quantity": quantity,
                "Duration": f"{duration}s ({duration//60}m)",
                "Chunks": chunks,
                "Chunk Size": f"{quantity/chunks:.6f}",
            })
            if confirmed:
                from src.advanced.twap import TWAPStrategy
                twap = TWAPStrategy(symbol, side, quantity, duration, chunks)
                twap.execute()
            else:
                print_warn("Order cancelled.")

        elif choice == "6":
            # Grid
            print_header("Grid Trading")
            symbol = str(prompt_input("Symbol", "BTCUSDT", validate_symbol, str)).upper()
            lower = float(prompt_input("Lower Price ($)", None, validate_price, float))
            upper = float(prompt_input("Upper Price ($)", None, validate_price, float))
            levels = int(prompt_input("Grid Levels", "10", None, int))
            qty = float(prompt_input("Quantity per Level", None, validate_quantity, float))

            confirmed = confirm_order({
                "Type": "Grid Trading",
                "Symbol": symbol,
                "Range": f"${lower:,.2f} — ${upper:,.2f}",
                "Levels": levels,
                "Qty/Level": qty,
            })
            if confirmed:
                from src.advanced.grid import GridStrategy
                grid = GridStrategy(symbol, lower, upper, levels, qty)
                grid.execute()
            else:
                print_warn("Order cancelled.")

        elif choice == "7":
            # Historical Analysis
            print_header("Historical Data Analysis")
            top_n = int(prompt_input("Top N coins to show", "10", None, int))
            from src.analysis.historical_analysis import load_historical_data, print_report
            trades = load_historical_data()
            if trades:
                print_report(trades, top_n=top_n)

        elif choice == "8":
            # Fear & Greed
            print_header("Fear & Greed Index")
            from src.analysis.fear_greed import load_fear_greed_data, print_report as fg_report
            data = load_fear_greed_data()
            if data:
                fg_report(data, show_signal=True)

        elif choice == "9":
            # Account Info
            print_header("Account & Positions")
            try:
                price = client.get_current_price("BTCUSDT")
                balance = client.get_account_balance()
                print(f"  {DIM}{'BTCUSDT Price':<16}{RESET} {WHITE}{BOLD}${price:,.2f}{RESET}")
                if balance:
                    total = balance.get("balance", "N/A")
                    avail = balance.get("availableBalance", "N/A")
                    print(f"  {DIM}{'Total Balance':<16}{RESET} {WHITE}{BOLD}{total} USDT{RESET}")
                    print(f"  {DIM}{'Available':<16}{RESET} {WHITE}{BOLD}{avail} USDT{RESET}")

                # Show open positions
                positions = client.client.futures_position_information(symbol="BTCUSDT")
                for p in positions:
                    amt = float(p.get("positionAmt", 0))
                    if amt != 0:
                        pnl = float(p.get("unRealizedProfit", 0))
                        entry = float(p.get("entryPrice", 0))
                        pnl_color = GREEN if pnl >= 0 else RED
                        print(f"\n  {BOLD}Open Position:{RESET}")
                        print(f"  {DIM}{'Symbol':<16}{RESET} {WHITE}{BOLD}{p['symbol']}{RESET}")
                        print(f"  {DIM}{'Amount':<16}{RESET} {WHITE}{BOLD}{p['positionAmt']}{RESET}")
                        print(f"  {DIM}{'Entry Price':<16}{RESET} {WHITE}{BOLD}${entry:,.2f}{RESET}")
                        print(f"  {DIM}{'Unrealized PnL':<16}{RESET} {pnl_color}{BOLD}${pnl:,.2f}{RESET}")
            except Exception as e:
                print_error(f"Failed to fetch account info: {e}")

        else:
            print_warn("Invalid choice. Please select 0-9.")


# ─── Direct CLI Mode ──────────────────────────────────────────────────────────

def build_parser():
    """Build argparse parser for direct CLI mode."""
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description=f"{BOLD}Binance Futures Trading Bot{RESET} — Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{BOLD}Direct Mode Examples:{RESET}
  python cli.py market BTCUSDT BUY 0.002
  python cli.py limit  BTCUSDT BUY 0.002 60000
  python cli.py stop   BTCUSDT SELL 0.002 58000 57800

{BOLD}Interactive Mode:{RESET}
  python cli.py
  python cli.py --interactive
""",
    )

    sub = parser.add_subparsers(dest="command", help="Order type")

    # Market
    m = sub.add_parser("market", help="Place a market order")
    m.add_argument("symbol", help="Trading pair (e.g., BTCUSDT)")
    m.add_argument("side", choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    m.add_argument("quantity", type=float, help="Order quantity")

    # Limit
    l = sub.add_parser("limit", help="Place a limit order")
    l.add_argument("symbol", help="Trading pair")
    l.add_argument("side", choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    l.add_argument("quantity", type=float, help="Order quantity")
    l.add_argument("price", type=float, help="Limit price")

    # Stop-Limit
    s = sub.add_parser("stop", help="Place a stop-limit order")
    s.add_argument("symbol", help="Trading pair")
    s.add_argument("side", choices=["BUY", "SELL", "buy", "sell"], help="BUY or SELL")
    s.add_argument("quantity", type=float, help="Order quantity")
    s.add_argument("stop_price", type=float, help="Stop trigger price")
    s.add_argument("limit_price", type=float, help="Limit price after trigger")

    # Interactive flag
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Launch interactive menu mode")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Interactive mode (default if no command given)
    if args.interactive or args.command is None:
        interactive_menu()
        return

    # Direct mode
    banner()

    try:
        client = BinanceClient()
        print_success("Connected to Binance Futures Testnet")
    except Exception as e:
        print_error(f"Failed to connect: {e}")
        sys.exit(1)

    # Validate common inputs
    try:
        symbol = args.symbol.upper()
        side = args.side.upper()
        validate_symbol(symbol)
        validate_side(side)
        validate_quantity(args.quantity)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)

    if args.command == "market":
        handle_market_order(client, symbol, side, args.quantity)

    elif args.command == "limit":
        try:
            validate_price(args.price)
        except ValueError as e:
            print_error(str(e))
            sys.exit(1)
        handle_limit_order(client, symbol, side, args.quantity, args.price)

    elif args.command == "stop":
        try:
            validate_price(args.stop_price)
            validate_price(args.limit_price)
        except ValueError as e:
            print_error(str(e))
            sys.exit(1)
        handle_stop_limit_order(client, symbol, side, args.quantity, args.stop_price, args.limit_price)


if __name__ == "__main__":
    main()

"""
Input Validation Module for Binance Futures Trading Bot.

This module provides validation functions that verify user inputs BEFORE
they are sent to the Binance API. Each function raises a ValueError with
a clear message if the input is invalid, or returns True if valid.

Validating inputs locally prevents unnecessary API calls, avoids cryptic
Binance error messages, and makes the bot more user-friendly.

Usage:
    from src.validators import validate_symbol, validate_side, validate_quantity
    validate_symbol("BTCUSDT")   # Returns True
    validate_symbol("btcusdt")   # Raises ValueError
"""


def validate_symbol(symbol: str) -> bool:
    """
    Validate that a trading symbol is in the correct format.

    Binance Futures symbols must be:
    - Uppercase letters only (e.g., BTCUSDT, not btcusdt)
    - End with 'USDT' (we only support USDT-M futures contracts)
    - At least 5 characters long (e.g., minimum is like BNBUSDT)

    Args:
        symbol: The trading pair symbol to validate (e.g., "BTCUSDT").

    Returns:
        True if the symbol is valid.

    Raises:
        ValueError: If the symbol format is invalid.

    Examples:
        >>> validate_symbol("BTCUSDT")
        True
        >>> validate_symbol("btcusdt")
        ValueError: Symbol must be uppercase...
    """
    if not isinstance(symbol, str):
        raise ValueError(f"Symbol must be a string, got {type(symbol).__name__}")

    if not symbol.isupper():
        raise ValueError(
            f"Symbol must be uppercase. Got '{symbol}', did you mean '{symbol.upper()}'?"
        )

    if not symbol.endswith("USDT"):
        raise ValueError(
            f"Symbol must end with 'USDT' (USDT-M futures). Got '{symbol}'."
        )

    if len(symbol) < 5:
        raise ValueError(
            f"Symbol is too short. Expected format like 'BTCUSDT', got '{symbol}'."
        )

    # Check that symbol contains only alphabetic characters
    if not symbol.isalpha():
        raise ValueError(
            f"Symbol must contain only letters. Got '{symbol}'."
        )

    return True


def validate_side(side: str) -> bool:
    """
    Validate that the order side is either BUY or SELL.

    In futures trading:
    - BUY = Open a long position (profit when price goes up)
           or close a short position
    - SELL = Open a short position (profit when price goes down)
            or close a long position

    Args:
        side: The order side, must be "BUY" or "SELL".

    Returns:
        True if the side is valid.

    Raises:
        ValueError: If the side is not BUY or SELL.
    """
    if not isinstance(side, str):
        raise ValueError(f"Side must be a string, got {type(side).__name__}")

    side_upper = side.upper()
    if side_upper not in ("BUY", "SELL"):
        raise ValueError(
            f"Side must be 'BUY' or 'SELL'. Got '{side}'. "
            f"BUY = go long / close short, SELL = go short / close long."
        )

    return True


def validate_quantity(quantity: float) -> bool:
    """
    Validate that the order quantity is a positive number.

    The quantity represents how much of the asset to trade.
    For example, quantity=0.01 for BTCUSDT means 0.01 Bitcoin.

    Args:
        quantity: The amount to trade (must be > 0).

    Returns:
        True if the quantity is valid.

    Raises:
        ValueError: If the quantity is not a positive number.
    """
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(
            f"Quantity must be a number. Got '{quantity}' ({type(quantity).__name__})."
        )

    if quantity <= 0:
        raise ValueError(
            f"Quantity must be greater than 0. Got {quantity}. "
            f"Example: 0.001 for BTC, 0.01 for ETH."
        )

    return True


def validate_price(price: float) -> bool:
    """
    Validate that a price value is a positive number.

    This is used for limit prices, stop prices, take-profit prices, etc.
    The price must be a positive float representing the USD value.

    Args:
        price: The price value to validate (must be > 0).

    Returns:
        True if the price is valid.

    Raises:
        ValueError: If the price is not a positive number.
    """
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValueError(
            f"Price must be a number. Got '{price}' ({type(price).__name__})."
        )

    if price <= 0:
        raise ValueError(
            f"Price must be greater than 0. Got {price}."
        )

    return True


def validate_stop_price(stop_price: float, current_price: float, side: str) -> bool:
    """
    Validate that a stop price has a logical relationship to the current price.

    Stop-loss logic explained:
    - For a LONG position (BUY side): The stop-loss should be BELOW the
      current price. If the price drops to this level, the position is
      closed to limit losses.
    - For a SHORT position (SELL side): The stop-loss should be ABOVE the
      current price. If the price rises to this level, the position is
      closed to limit losses.

    Args:
        stop_price:    The stop price to validate.
        current_price: The current market price of the asset.
        side:          The order side ("BUY" or "SELL").

    Returns:
        True if the stop price is logically valid.

    Raises:
        ValueError: If the stop price doesn't make logical sense for the
                    given side.
    """
    # First validate the individual values
    validate_price(stop_price)
    validate_price(current_price)
    validate_side(side)

    side = side.upper()

    if side == "SELL":
        # For SELL (stop-loss on a long position):
        # Stop price should be below current price
        # When price drops to stop_price, it triggers a sell to cut losses
        if stop_price >= current_price:
            raise ValueError(
                f"For a SELL stop order (long position stop-loss), stop price "
                f"({stop_price}) must be BELOW current price ({current_price}). "
                f"The stop triggers when the price drops to this level."
            )

    elif side == "BUY":
        # For BUY (stop-loss on a short position):
        # Stop price should be above current price
        # When price rises to stop_price, it triggers a buy to cut losses
        if stop_price <= current_price:
            raise ValueError(
                f"For a BUY stop order (short position stop-loss), stop price "
                f"({stop_price}) must be ABOVE current price ({current_price}). "
                f"The stop triggers when the price rises to this level."
            )

    return True


# ---------------------------------------------------------------------------
# Self-test: run all validators with sample inputs when executed directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Validator Module — Self-Test")
    print("=" * 60)

    # Test valid inputs
    tests_passed = 0
    tests_failed = 0

    test_cases = [
        ("validate_symbol('BTCUSDT')", lambda: validate_symbol("BTCUSDT")),
        ("validate_symbol('ETHUSDT')", lambda: validate_symbol("ETHUSDT")),
        ("validate_side('BUY')", lambda: validate_side("BUY")),
        ("validate_side('SELL')", lambda: validate_side("SELL")),
        ("validate_quantity(0.001)", lambda: validate_quantity(0.001)),
        ("validate_quantity(100)", lambda: validate_quantity(100)),
        ("validate_price(50000.50)", lambda: validate_price(50000.50)),
        ("validate_stop_price(49000, 50000, 'SELL')", lambda: validate_stop_price(49000, 50000, "SELL")),
        ("validate_stop_price(51000, 50000, 'BUY')", lambda: validate_stop_price(51000, 50000, "BUY")),
    ]

    for name, test_fn in test_cases:
        try:
            result = test_fn()
            print(f"  ✅ PASS: {name} → {result}")
            tests_passed += 1
        except Exception as e:
            print(f"  ❌ FAIL: {name} → {e}")
            tests_failed += 1

    # Test invalid inputs (should raise ValueError)
    invalid_cases = [
        ("validate_symbol('btcusdt')", lambda: validate_symbol("btcusdt")),
        ("validate_symbol('BTCETH')", lambda: validate_symbol("BTCETH")),
        ("validate_side('HOLD')", lambda: validate_side("HOLD")),
        ("validate_quantity(-1)", lambda: validate_quantity(-1)),
        ("validate_quantity(0)", lambda: validate_quantity(0)),
        ("validate_price(-100)", lambda: validate_price(-100)),
        ("validate_stop_price(51000, 50000, 'SELL')", lambda: validate_stop_price(51000, 50000, "SELL")),
    ]

    for name, test_fn in invalid_cases:
        try:
            test_fn()
            print(f"  ❌ FAIL: {name} → Should have raised ValueError!")
            tests_failed += 1
        except ValueError as e:
            print(f"  ✅ PASS: {name} → Correctly raised ValueError")
            tests_passed += 1

    print(f"\n  Results: {tests_passed} passed, {tests_failed} failed")
    print("=" * 60)

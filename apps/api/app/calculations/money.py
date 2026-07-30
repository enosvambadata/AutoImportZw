"""Money primitives for AutoBid Intelligence.

All monetary arithmetic uses :class:`decimal.Decimal`. Floats are never used for money.
Rounding is explicit: money to 2dp ROUND_HALF_UP; ratios to 4dp for display.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Number = Decimal | int | str | float

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
ZERO = Decimal("0.00")


def to_decimal(value: Number | None, default: Number = "0") -> Decimal:
    """Coerce any supported input to a Decimal, safely.

    Floats are routed through ``str`` so we never inherit binary float error.
    ``None`` collapses to ``default``.
    """
    if value is None:
        value = default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Cannot convert {value!r} to Decimal") from exc


def money(value: Number | None) -> Decimal:
    """Round a value to 2 decimal places using banker-safe HALF_UP."""
    return to_decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def ratio(value: Number | None) -> Decimal:
    """Round a ratio/percentage to 4 decimal places for stable display."""
    return to_decimal(value).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def safe_div(numerator: Number | None, denominator: Number | None) -> Decimal | None:
    """Divide two Decimals, returning ``None`` on a zero/None denominator."""
    d = to_decimal(denominator)
    if d == 0:
        return None
    return to_decimal(numerator) / d


def clamp(value: Decimal, low: Decimal | None = None, high: Decimal | None = None) -> Decimal:
    if low is not None and value < low:
        return low
    if high is not None and value > high:
        return high
    return value

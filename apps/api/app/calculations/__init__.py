"""Pure, deterministic calculation engine (source of truth for all money maths)."""

from .engine import (
    AppraisalInputs,
    BidLadderRung,
    CalculationResult,
    CostRange,
    Scenario,
    calculate,
)
from .fees import FeeBand, FeeResult, FeeSchedule, fixed, flat_percentage, percentage_plus_fixed
from .money import money, ratio, safe_div, to_decimal

__all__ = [
    "AppraisalInputs",
    "BidLadderRung",
    "CalculationResult",
    "CostRange",
    "Scenario",
    "calculate",
    "FeeBand",
    "FeeResult",
    "FeeSchedule",
    "fixed",
    "flat_percentage",
    "percentage_plus_fixed",
    "money",
    "ratio",
    "safe_div",
    "to_decimal",
]

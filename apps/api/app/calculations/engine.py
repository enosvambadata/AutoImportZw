"""AutoBid Intelligence calculation engine.

Deterministic, framework-free, Decimal-based. This module is the single source of truth
for every monetary figure the product shows. It is depended on by the API services and is
mirrored by *no* frontend logic.

Key outputs (see docs/CALCULATION_ENGINE.md):
- safe / absolute / break-even hammer bids (fees solved iteratively via bisection)
- expected / pessimistic / optimistic profit at a reference hammer price
- ROI (profit-on-cost and profit-on-hammer), margin
- a bid ladder and a sensitivity matrix
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .fees import FeeSchedule
from .money import ZERO, money, ratio, safe_div, to_decimal


class Scenario(str, Enum):
    PESSIMISTIC = "pessimistic"
    EXPECTED = "expected"
    OPTIMISTIC = "optimistic"


@dataclass(frozen=True)
class CostRange:
    """A non-bid cost with a low/expected/high band (e.g. repairs, transport)."""

    name: str
    category: str
    estimated: Decimal
    minimum: Decimal | None = None
    maximum: Decimal | None = None

    def at(self, scenario: Scenario) -> Decimal:
        if scenario is Scenario.PESSIMISTIC:
            return to_decimal(self.maximum if self.maximum is not None else self.estimated)
        if scenario is Scenario.OPTIMISTIC:
            return to_decimal(self.minimum if self.minimum is not None else self.estimated)
        return to_decimal(self.estimated)


@dataclass
class AppraisalInputs:
    # Sale-side
    expected_retail: Decimal
    conservative_retail: Decimal
    optimistic_retail: Decimal
    expected_discount: Decimal = ZERO
    # Costs (non-bid). Auction buyer fee is derived from the fee_schedule, not listed here.
    costs: list[CostRange] = field(default_factory=list)
    fee_schedule: FeeSchedule = field(default_factory=FeeSchedule)
    # Profit policy
    target_profit: Decimal = Decimal("1200")
    risk_reserve: Decimal = ZERO  # full recommended reserve (used by safe max)
    mandatory_min_reserve: Decimal = Decimal("150")  # floor reserve (used by absolute max)
    min_roi: Decimal = Decimal("0.15")
    # Context
    current_bid: Decimal | None = None
    guide_price: Decimal | None = None
    above_absolute_delta: Decimal = Decimal("500")
    holding_cost_per_day: Decimal = ZERO
    estimated_days_to_sell: int = 45

    # ---- derived helpers ----
    def costs_total(self, scenario: Scenario) -> Decimal:
        return sum((c.at(scenario) for c in self.costs), ZERO)

    def net_sale(self, scenario: Scenario) -> Decimal:
        if scenario is Scenario.PESSIMISTIC:
            sale = self.conservative_retail
            discount = self.expected_discount
        elif scenario is Scenario.OPTIMISTIC:
            sale = self.optimistic_retail
            discount = self.expected_discount / 2
        else:
            sale = self.expected_retail
            discount = self.expected_discount
        return to_decimal(sale) - to_decimal(discount)

    @property
    def reference_hammer(self) -> Decimal:
        """Hammer price used to anchor headline profit figures.

        Priority: live current bid -> auction guide price -> the safe maximum bid.
        Evaluating "if we win at this price, what do we make" is the dealer's real question.
        """
        if self.current_bid is not None and to_decimal(self.current_bid) > 0:
            return to_decimal(self.current_bid)
        if self.guide_price is not None and to_decimal(self.guide_price) > 0:
            return to_decimal(self.guide_price)
        return self.safe_max_bid()

    # ---- profit ----
    def profit_at(self, hammer: Decimal, scenario: Scenario,
                  extra_days: int = 0, sale_scale: Decimal = Decimal("1"),
                  cost_scale: Decimal = Decimal("1"),
                  discount_override: Decimal | None = None) -> Decimal:
        """Profit at a hammer price under a scenario, with optional sensitivity scaling."""
        hammer = to_decimal(hammer)
        net_sale = self.net_sale(scenario) * sale_scale
        if discount_override is not None:
            base_sale = (self.conservative_retail if scenario is Scenario.PESSIMISTIC
                         else self.optimistic_retail if scenario is Scenario.OPTIMISTIC
                         else self.expected_retail)
            net_sale = (to_decimal(base_sale) * sale_scale) - to_decimal(discount_override)
        fee = self.fee_schedule.compute(hammer).gross
        costs = self.costs_total(scenario) * cost_scale
        holding = self.holding_cost_per_day * to_decimal(extra_days)
        return net_sale - (hammer + fee + costs + holding)

    # ---- bid solving (bisection; hammer+fee(hammer) is monotonic increasing) ----
    def _solve_max_hammer(self, scenario: Scenario, deduction: Decimal) -> Decimal:
        """Highest hammer H where net_sale − (H + fee(H) + costs) − deduction == 0.

        Returns 0 if the target cannot be met even at a zero hammer.
        """
        net_sale = self.net_sale(scenario)
        costs = self.costs_total(scenario)
        target_surplus = net_sale - costs - deduction  # value available for hammer+fee

        def g(h: Decimal) -> Decimal:
            return target_surplus - (h + self.fee_schedule.compute(h).gross)

        if g(ZERO) <= 0:
            return ZERO
        lo, hi = ZERO, target_surplus  # root is below target_surplus because fee>=0
        for _ in range(80):  # ~£0.00 precision well within 80 halvings
            mid = (lo + hi) / 2
            if g(mid) > 0:
                lo = mid
            else:
                hi = mid
            if hi - lo <= Decimal("0.005"):
                break
        return money(lo)

    def safe_max_bid(self) -> Decimal:
        return self._solve_max_hammer(
            Scenario.PESSIMISTIC, self.risk_reserve + self.target_profit
        )

    def absolute_max_bid(self) -> Decimal:
        return self._solve_max_hammer(
            Scenario.EXPECTED, self.mandatory_min_reserve + self.target_profit
        )

    def break_even_bid(self) -> Decimal:
        return self._solve_max_hammer(Scenario.EXPECTED, ZERO)


@dataclass
class BidLadderRung:
    label: str
    hammer: Decimal
    fee: Decimal
    total_cash_required: Decimal
    expected_profit: Decimal
    worst_case_profit: Decimal
    roi_on_cash: Decimal | None
    margin: Decimal | None
    exceeds_absolute: bool


@dataclass
class CalculationResult:
    safe_max_bid: Decimal
    absolute_max_bid: Decimal
    break_even_bid: Decimal
    reference_hammer: Decimal
    expected_profit: Decimal
    pessimistic_profit: Decimal
    optimistic_profit: Decimal
    total_cash_invested: Decimal
    roi_on_cost: Decimal | None
    roi_on_hammer: Decimal | None
    margin: Decimal | None
    meets_target: bool
    meets_roi: bool
    bid_ladder: list[BidLadderRung]
    sensitivity: dict
    fee_at_reference: Decimal

    def to_dict(self) -> dict:
        def d(x):
            return None if x is None else str(x)

        return {
            "safe_max_bid": d(self.safe_max_bid),
            "absolute_max_bid": d(self.absolute_max_bid),
            "break_even_bid": d(self.break_even_bid),
            "reference_hammer": d(self.reference_hammer),
            "expected_profit": d(self.expected_profit),
            "pessimistic_profit": d(self.pessimistic_profit),
            "optimistic_profit": d(self.optimistic_profit),
            "total_cash_invested": d(self.total_cash_invested),
            "roi_on_cost": d(self.roi_on_cost),
            "roi_on_hammer": d(self.roi_on_hammer),
            "margin": d(self.margin),
            "meets_target": self.meets_target,
            "meets_roi": self.meets_roi,
            "fee_at_reference": d(self.fee_at_reference),
            "bid_ladder": [
                {
                    "label": r.label,
                    "hammer": d(r.hammer),
                    "fee": d(r.fee),
                    "total_cash_required": d(r.total_cash_required),
                    "expected_profit": d(r.expected_profit),
                    "worst_case_profit": d(r.worst_case_profit),
                    "roi_on_cash": d(r.roi_on_cash),
                    "margin": d(r.margin),
                    "exceeds_absolute": r.exceeds_absolute,
                }
                for r in self.bid_ladder
            ],
            "sensitivity": self.sensitivity,
        }


def _cash_required(inp: AppraisalInputs, hammer: Decimal,
                   scenario: Scenario = Scenario.EXPECTED) -> Decimal:
    fee = inp.fee_schedule.compute(hammer).gross
    return money(hammer + fee + inp.costs_total(scenario))


def _ladder_rung(inp: AppraisalInputs, label: str, hammer: Decimal,
                 absolute_max: Decimal) -> BidLadderRung:
    hammer = money(hammer)
    fee = inp.fee_schedule.compute(hammer).gross
    cash = _cash_required(inp, hammer)
    exp = money(inp.profit_at(hammer, Scenario.EXPECTED))
    worst = money(inp.profit_at(hammer, Scenario.PESSIMISTIC))
    net_sale = inp.net_sale(Scenario.EXPECTED)
    return BidLadderRung(
        label=label,
        hammer=hammer,
        fee=money(fee),
        total_cash_required=cash,
        expected_profit=exp,
        worst_case_profit=worst,
        roi_on_cash=(ratio(safe_div(exp, cash)) if cash else None),
        margin=(ratio(safe_div(exp, net_sale)) if net_sale else None),
        exceeds_absolute=hammer > absolute_max,
    )


def _build_sensitivity(inp: AppraisalInputs, ref: Decimal) -> dict:
    price_deltas = [Decimal("-0.15"), Decimal("-0.10"), Decimal("-0.05"),
                    Decimal("0"), Decimal("0.05"), Decimal("0.10")]
    cost_deltas = [Decimal("-0.10"), Decimal("0"), Decimal("0.10"),
                   Decimal("0.25"), Decimal("0.50")]
    matrix = []
    for pd in price_deltas:
        row = []
        for cd in cost_deltas:
            profit = inp.profit_at(
                ref, Scenario.EXPECTED,
                sale_scale=Decimal("1") + pd,
                cost_scale=Decimal("1") + cd,
            )
            row.append(str(money(profit)))
        matrix.append(row)

    days = [0, 15, 30, 45, 60, 90]
    days_row = [
        str(money(inp.profit_at(ref, Scenario.EXPECTED, extra_days=extra)))
        for extra in days
    ]

    discount_steps = [ZERO, Decimal("250"), Decimal("500"), Decimal("1000"), Decimal("1500")]
    discount_row = [
        str(money(inp.profit_at(ref, Scenario.EXPECTED, discount_override=ds)))
        for ds in discount_steps
    ]

    return {
        "price_deltas": [str(x) for x in price_deltas],
        "cost_deltas": [str(x) for x in cost_deltas],
        "profit_matrix": matrix,  # rows=price, cols=cost
        "days_axis": days,
        "days_profit": days_row,
        "discount_axis": [str(x) for x in discount_steps],
        "discount_profit": discount_row,
    }


def calculate(inp: AppraisalInputs) -> CalculationResult:
    """Run the full calculation and return a structured, serialisable result."""
    safe = inp.safe_max_bid()
    absolute = inp.absolute_max_bid()
    break_even = inp.break_even_bid()
    ref = inp.reference_hammer

    expected_profit = money(inp.profit_at(ref, Scenario.EXPECTED))
    pessimistic_profit = money(inp.profit_at(ref, Scenario.PESSIMISTIC))
    optimistic_profit = money(inp.profit_at(ref, Scenario.OPTIMISTIC))

    cash = _cash_required(inp, ref)
    net_sale = inp.net_sale(Scenario.EXPECTED)
    roi_on_cost = ratio(safe_div(expected_profit, cash)) if cash else None
    roi_on_hammer = ratio(safe_div(expected_profit, ref)) if ref else None
    margin = ratio(safe_div(expected_profit, net_sale)) if net_sale else None

    midpoint = money((safe + absolute) / 2)
    above = money(absolute + inp.above_absolute_delta)
    rungs: list[BidLadderRung] = []
    if inp.current_bid is not None and to_decimal(inp.current_bid) > 0:
        rungs.append(_ladder_rung(inp, "Current bid", to_decimal(inp.current_bid), absolute))
    rungs.append(_ladder_rung(inp, "Safe maximum", safe, absolute))
    rungs.append(_ladder_rung(inp, "Safe/absolute midpoint", midpoint, absolute))
    rungs.append(_ladder_rung(inp, "Absolute maximum", absolute, absolute))
    rungs.append(_ladder_rung(inp, "Above absolute (do not exceed)", above, absolute))

    return CalculationResult(
        safe_max_bid=safe,
        absolute_max_bid=absolute,
        break_even_bid=break_even,
        reference_hammer=money(ref),
        expected_profit=expected_profit,
        pessimistic_profit=pessimistic_profit,
        optimistic_profit=optimistic_profit,
        total_cash_invested=cash,
        roi_on_cost=roi_on_cost,
        roi_on_hammer=roi_on_hammer,
        margin=margin,
        meets_target=expected_profit >= inp.target_profit,
        meets_roi=(roi_on_cost is not None and roi_on_cost >= inp.min_roi),
        bid_ladder=rungs,
        sensitivity=_build_sensitivity(inp, ref),
        fee_at_reference=money(inp.fee_schedule.compute(ref).gross),
    )

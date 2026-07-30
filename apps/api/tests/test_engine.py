"""Calculation-engine unit tests: bids, scenarios, ROI, iterative fees, sensitivity."""

from decimal import Decimal

import pytest

from app.calculations.engine import AppraisalInputs, CostRange, Scenario, calculate
from app.calculations.fees import FeeBand, FeeSchedule, fixed, flat_percentage


def D(x):
    return Decimal(str(x))


def approx(a: Decimal, b, tol="1.00"):
    return abs(D(a) - D(b)) <= D(tol)


def base_inputs(**overrides) -> AppraisalInputs:
    kwargs = dict(
        expected_retail=D("10000"),
        conservative_retail=D("9500"),
        optimistic_retail=D("10800"),
        expected_discount=D("200"),
        costs=[
            CostRange("Preparation", "service", D("800"), D("600"), D("1200")),
            CostRange("Transport", "transport", D("150")),
        ],
        fee_schedule=flat_percentage(D("0.08"), vat_applicable=False),
        target_profit=D("1000"),
        risk_reserve=D("300"),
        mandatory_min_reserve=D("150"),
        min_roi=D("0.15"),
    )
    kwargs.update(overrides)
    return AppraisalInputs(**kwargs)


def test_break_even_profit_is_zero_at_break_even_bid():
    inp = base_inputs()
    be = inp.break_even_bid()
    assert approx(inp.profit_at(be, Scenario.EXPECTED), 0)


def test_safe_max_pessimistic_profit_equals_target_plus_reserve():
    inp = base_inputs()
    safe = inp.safe_max_bid()
    # Safe max uses conservative sale + high costs + reserve + target; the pessimistic
    # scenario is exactly those assumptions, so worst-case profit == target + reserve.
    assert approx(inp.profit_at(safe, Scenario.PESSIMISTIC), D("1300"))


def test_absolute_max_expected_profit_equals_target_plus_min_reserve():
    inp = base_inputs()
    ab = inp.absolute_max_bid()
    assert approx(inp.profit_at(ab, Scenario.EXPECTED), D("1150"))


def test_bid_ordering_safe_le_absolute_le_breakeven():
    inp = base_inputs()
    assert inp.safe_max_bid() <= inp.absolute_max_bid() <= inp.break_even_bid()


def test_zero_target_profit_raises_bids():
    lo = base_inputs(target_profit=D("1000"))
    hi = base_inputs(target_profit=D("0"))
    assert hi.absolute_max_bid() > lo.absolute_max_bid()


def test_high_repair_costs_reduce_bid():
    cheap = base_inputs()
    dear = base_inputs(costs=[CostRange("Repairs", "mechanical", D("4000"), D("3500"), D("5000"))])
    assert dear.safe_max_bid() < cheap.safe_max_bid()


def test_negative_profit_when_hammer_too_high():
    inp = base_inputs()
    # Pay well above break-even -> expected profit is negative.
    profit = inp.profit_at(inp.break_even_bid() + D("2000"), Scenario.EXPECTED)
    assert profit < 0


def test_unaffordable_target_returns_zero_bid():
    # Target profit larger than the entire margin -> cannot bid anything.
    inp = base_inputs(target_profit=D("50000"))
    assert inp.safe_max_bid() == D("0.00")


def test_roi_and_margin_signs():
    inp = base_inputs(current_bid=D("6000"))
    res = calculate(inp)
    assert res.expected_profit > 0
    assert res.roi_on_cost is not None and res.roi_on_cost > 0
    assert res.roi_on_hammer is not None and res.roi_on_hammer > 0
    assert res.margin is not None and 0 < res.margin < 1


def test_iterative_fee_across_tier_boundary_is_consistent():
    # Fee jumps at £6000. Solve must use the fee that actually applies at the solved bid.
    sched = FeeSchedule(
        vat_applicable=False,
        bands=[
            FeeBand(percentage=D("0.05"), upper_bound=D("6000")),
            FeeBand(percentage=D("0.10"), lower_bound=D("6000")),
        ],
    )
    inp = base_inputs(fee_schedule=sched)
    be = inp.break_even_bid()
    # Expected profit at the solved break-even must be ~0 with the correct tier fee applied.
    assert approx(inp.profit_at(be, Scenario.EXPECTED), 0, tol="2.00")


def test_scenarios_are_ordered():
    inp = base_inputs(current_bid=D("6000"))
    res = calculate(inp)
    assert res.pessimistic_profit < res.expected_profit < res.optimistic_profit


def test_reference_hammer_priority_current_over_guide():
    inp = base_inputs(current_bid=D("5000"), guide_price=D("7000"))
    assert inp.reference_hammer == D("5000")
    inp2 = base_inputs(guide_price=D("7000"))
    assert inp2.reference_hammer == D("7000")


def test_bid_ladder_flags_exceeding_absolute():
    inp = base_inputs(current_bid=D("6000"))
    res = calculate(inp)
    above = next(r for r in res.bid_ladder if r.label.startswith("Above"))
    assert above.exceeds_absolute is True
    safe = next(r for r in res.bid_ladder if r.label == "Safe maximum")
    assert safe.exceeds_absolute is False


def test_sensitivity_matrix_shape_and_monotonicity():
    inp = base_inputs(current_bid=D("6000"))
    res = calculate(inp)
    matrix = res.sensitivity["profit_matrix"]
    assert len(matrix) == 6  # price deltas
    assert all(len(row) == 5 for row in matrix)  # cost deltas
    # Higher selling price -> higher profit (compare first vs last row, same cost col).
    assert D(matrix[-1][0]) > D(matrix[0][0])
    # Higher costs -> lower profit (compare first vs last col, same price row).
    assert D(matrix[0][-1]) < D(matrix[0][0])


def test_fee_with_vat_included_in_cash_required():
    inp = base_inputs(
        fee_schedule=fixed(D("300"), vat_applicable=True, vat_rate=D("0.20")),
        current_bid=D("6000"),
    )
    res = calculate(inp)
    # cash = hammer 6000 + fee gross 360 + costs (800+150) = 7310
    assert res.total_cash_invested == D("7310.00")
    assert res.fee_at_reference == D("360.00")


def test_missing_optional_costs_defaults_to_estimated():
    c = CostRange("X", "other", D("500"))  # no min/max
    assert c.at(Scenario.PESSIMISTIC) == D("500")
    assert c.at(Scenario.OPTIMISTIC) == D("500")


def test_result_is_serialisable():
    res = calculate(base_inputs(current_bid=D("6000")))
    d = res.to_dict()
    assert set(["safe_max_bid", "absolute_max_bid", "break_even_bid", "bid_ladder"]).issubset(d)
    assert isinstance(d["bid_ladder"], list)

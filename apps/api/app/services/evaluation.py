"""Orchestration: turn appraisal inputs into calculation + risk + recommendation output.

Used by both the calculation-preview endpoint (no persistence) and the appraisal write path.
Everything downstream of this is display only — this is where the engines are combined.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..calculations.engine import AppraisalInputs, CostRange, calculate
from ..calculations.fees import FeeBand, FeeSchedule
from ..calculations.money import to_decimal
from .recommendation import (
    Confidence,
    RecommendationInputs,
    recommend,
)
from .risk import RiskInputs, assess

# Cost categories that are *derived* from the fee schedule, not entered as line items.
DERIVED_COST_CATEGORIES = {"AUCTION_FEE", "FEE_VAT"}

REQUIRED_VALUATION_FIELDS = {
    "expected_retail_price": "Expected retail price",
    "conservative_retail_price": "Conservative retail price",
    "optimistic_retail_price": "Optimistic retail price",
}


def build_fee_schedule(bands: list[dict[str, Any]], vat_rate: Decimal = Decimal("0.20")) -> FeeSchedule:
    """Build a :class:`FeeSchedule` from serialisable fee-band dicts.

    Each band dict may contain: fixed_fee, percentage, minimum_fee, maximum_fee,
    lower_bound, upper_bound, vat_applicable, stated_inclusive.
    """
    if not bands:
        return FeeSchedule(bands=[], vat_applicable=False)
    fee_bands = [
        FeeBand(
            fixed_fee=to_decimal(b.get("fixed_fee", 0)),
            percentage=to_decimal(b.get("percentage", 0)),
            minimum_fee=(to_decimal(b["minimum_fee"]) if b.get("minimum_fee") is not None else None),
            maximum_fee=(to_decimal(b["maximum_fee"]) if b.get("maximum_fee") is not None else None),
            lower_bound=(to_decimal(b["lower_bound"]) if b.get("lower_bound") is not None else None),
            upper_bound=(to_decimal(b["upper_bound"]) if b.get("upper_bound") is not None else None),
        )
        for b in bands
    ]
    first = bands[0]
    return FeeSchedule(
        bands=fee_bands,
        vat_applicable=bool(first.get("vat_applicable", True)),
        vat_rate=vat_rate,
        stated_inclusive=bool(first.get("stated_inclusive", False)),
    )


def _confidence_from_str(value: str | None) -> Confidence:
    try:
        return Confidence(str(value).upper())
    except (ValueError, AttributeError):
        return Confidence.MEDIUM


def evaluate(
    *,
    expected_retail: Decimal | None,
    conservative_retail: Decimal | None,
    optimistic_retail: Decimal | None,
    expected_discount: Decimal = Decimal("0"),
    costs: list[dict[str, Any]],
    fee_bands: list[dict[str, Any]],
    target_profit: Decimal,
    risk_reserve: Decimal,
    mandatory_min_reserve: Decimal,
    min_roi: Decimal,
    vat_rate: Decimal = Decimal("0.20"),
    current_bid: Decimal | None = None,
    guide_price: Decimal | None = None,
    above_absolute_delta: Decimal = Decimal("500"),
    estimated_days_to_sell: int = 45,
    holding_cost_per_day: Decimal = Decimal("0"),
    pricing_confidence: str | None = "MEDIUM",
    max_acceptable_pessimistic_loss: Decimal = Decimal("-500"),
    risk_inputs: RiskInputs | None = None,
    risk_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    # --- completeness check ---
    provided = {
        "expected_retail_price": expected_retail,
        "conservative_retail_price": conservative_retail,
        "optimistic_retail_price": optimistic_retail,
    }
    missing = [label for key, label in REQUIRED_VALUATION_FIELDS.items()
               if provided[key] is None]

    # --- risk (always runnable) ---
    risk_inputs = risk_inputs or RiskInputs()
    risk_inputs.estimated_days_to_sell = estimated_days_to_sell
    risk = assess(risk_inputs, weights=risk_weights)

    fee_schedule = build_fee_schedule(fee_bands, vat_rate=vat_rate)

    cost_ranges = [
        CostRange(
            name=c.get("name", c.get("category", "Cost")),
            category=c.get("category", "OTHER"),
            estimated=to_decimal(c.get("estimated_amount", 0)),
            minimum=(to_decimal(c["minimum_amount"]) if c.get("minimum_amount") is not None else None),
            maximum=(to_decimal(c["maximum_amount"]) if c.get("maximum_amount") is not None else None),
        )
        for c in costs
        if c.get("category") not in DERIVED_COST_CATEGORIES
    ]

    if missing:
        rec = recommend(RecommendationInputs(
            expected_profit=Decimal("0"),
            pessimistic_profit=Decimal("0"),
            target_profit=target_profit,
            roi_on_cost=None,
            min_roi=min_roi,
            risk_level=risk.level,
            critical_flags=risk.critical_flags,
            policy_blocks=risk.policy_blocks,
            missing_fields=missing,
        ))
        return {"calculation": None, "risk": risk.to_dict(), "recommendation": rec.to_dict()}

    inp = AppraisalInputs(
        expected_retail=to_decimal(expected_retail),
        conservative_retail=to_decimal(conservative_retail),
        optimistic_retail=to_decimal(optimistic_retail),
        expected_discount=to_decimal(expected_discount),
        costs=cost_ranges,
        fee_schedule=fee_schedule,
        target_profit=to_decimal(target_profit),
        risk_reserve=to_decimal(risk_reserve),
        mandatory_min_reserve=to_decimal(mandatory_min_reserve),
        min_roi=to_decimal(min_roi),
        current_bid=(to_decimal(current_bid) if current_bid is not None else None),
        guide_price=(to_decimal(guide_price) if guide_price is not None else None),
        above_absolute_delta=to_decimal(above_absolute_delta),
        estimated_days_to_sell=estimated_days_to_sell,
        holding_cost_per_day=to_decimal(holding_cost_per_day),
    )
    calc = calculate(inp)

    rec = recommend(RecommendationInputs(
        expected_profit=calc.expected_profit,
        pessimistic_profit=calc.pessimistic_profit,
        target_profit=to_decimal(target_profit),
        roi_on_cost=calc.roi_on_cost,
        min_roi=to_decimal(min_roi),
        risk_level=risk.level,
        critical_flags=risk.critical_flags,
        policy_blocks=risk.policy_blocks,
        history_warnings=risk.warning_flags,
        market_confidence=_confidence_from_str(pricing_confidence),
        estimated_days_to_sell=estimated_days_to_sell,
        current_bid=(to_decimal(current_bid) if current_bid is not None else None),
        absolute_max_bid=calc.absolute_max_bid,
        guide_price=(to_decimal(guide_price) if guide_price is not None else None),
        max_acceptable_pessimistic_loss=to_decimal(max_acceptable_pessimistic_loss),
    ))

    return {
        "calculation": calc.to_dict(),
        "risk": risk.to_dict(),
        "recommendation": rec.to_dict(),
    }

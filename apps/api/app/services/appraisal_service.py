"""Persist-and-evaluate service for appraisals.

Derives risk signals from the vehicle/history/market data, runs the evaluation, and writes
the cached result columns plus the RiskAssessment row. The engine remains the source of truth;
these columns are a denormalised cache for fast listing/filtering.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..calculations.money import safe_div, to_decimal
from ..models.appraisal import Appraisal, RiskAssessment
from ..models.catalogue import AuctionFeeBand, AuctionListing, Vehicle
from ..models.organisation import Dealership
from .evaluation import evaluate
from .risk import RiskInputs


def _age_years(vehicle: Vehicle) -> Decimal | None:
    ref = date.today()
    if vehicle.registration_date:
        days = (ref - vehicle.registration_date).days
        return to_decimal(round(days / 365.25, 1))
    if vehicle.model_year:
        return to_decimal(max(0, ref.year - vehicle.model_year))
    return None


def _repair_uncertainty(appraisal: Appraisal) -> Decimal:
    est = Decimal("0")
    spread = Decimal("0")
    for c in appraisal.cost_items:
        e = to_decimal(c.estimated_amount)
        est += e
        lo = to_decimal(c.minimum_amount) if c.minimum_amount is not None else e
        hi = to_decimal(c.maximum_amount) if c.maximum_amount is not None else e
        spread += (hi - lo)
    r = safe_div(spread, est)
    return to_decimal(r) if r is not None else Decimal("0")


def derive_risk_inputs(
    appraisal: Appraisal,
    vehicle: Vehicle,
    listing: AuctionListing | None,
    dealership: Dealership,
) -> RiskInputs:
    h = vehicle.history
    comps = appraisal.comparables
    comparable_count = len(comps)

    exp = to_decimal(appraisal.expected_retail_price) if appraisal.expected_retail_price else None
    cons = appraisal.conservative_retail_price
    opt = appraisal.optimistic_retail_price
    gap = Decimal("0")
    if exp and cons is not None and opt is not None and exp > 0:
        gap = to_decimal((to_decimal(opt) - to_decimal(cons)) / exp)

    unusually_low = False
    if comps and exp and exp > 0:
        asks = [to_decimal(c.asking_price) for c in comps if c.asking_price is not None]
        if asks:
            avg = sum(asks) / len(asks)
            unusually_low = avg < exp * Decimal("0.85")

    runner = (listing.runner_status if listing else None) or ""
    condition = listing.condition_grade if listing else None

    return RiskInputs(
        category_marker=vehicle.category_marker,
        stolen_marker=bool(h and h.stolen_marker),
        outstanding_finance=bool(h and h.finance_marker),
        write_off_marker=bool(h and h.write_off_marker),
        mileage_discrepancy=bool(h and h.mileage_discrepancy),
        imported=vehicle.imported,
        plate_changes=(h.plate_changes if h else 0),
        keeper_changes=(h.keeper_changes if h else (vehicle.previous_keepers or 0)),
        mot_fail_count=(h.mot_fail_count if h else 0),
        dangerous_defect_count=(h.dangerous_defect_count if h else 0),
        major_defect_count=(h.major_defect_count if h else 0),
        repeated_mot_failures=bool(h and h.repeated_failures),
        non_runner=(runner.upper() == "NON_RUNNER"),
        condition_grade=condition,
        repair_uncertainty_ratio=_repair_uncertainty(appraisal),
        missing_service_history=bool(h and (h.service_history_status or "").upper() == "NONE"),
        one_key_only=(vehicle.number_of_keys == 1),
        unusually_low_market_price=unusually_low,
        comparable_count=comparable_count if comparable_count else 3,
        valuation_gap_ratio=gap,
        age_years=_age_years(vehicle),
        mileage=vehicle.mileage,
        estimated_days_to_sell=appraisal.estimated_days_to_sell,
        allow_category_n=dealership.allow_category_n,
        allow_category_s=dealership.allow_category_s,
    )


async def _fee_bands_for(db: AsyncSession, listing: AuctionListing | None) -> list[dict]:
    if listing is None:
        return []
    rows = (await db.execute(
        select(AuctionFeeBand).where(AuctionFeeBand.auction_house_id == listing.auction_house_id)
    )).scalars().all()
    return [
        {
            "fixed_fee": b.fixed_fee,
            "percentage": b.percentage,
            "minimum_fee": b.minimum_fee,
            "maximum_fee": b.maximum_fee,
            "lower_bound": b.lower_bound,
            "upper_bound": b.upper_bound,
            "vat_applicable": b.vat_applicable,
            "stated_inclusive": b.stated_inclusive,
        }
        for b in rows
    ]


async def compute_and_store(db: AsyncSession, appraisal: Appraisal) -> dict:
    dealership = await db.get(Dealership, appraisal.dealership_id)
    vehicle = (await db.execute(
        select(Vehicle).options(selectinload(Vehicle.history))
        .where(Vehicle.id == appraisal.vehicle_id)
    )).scalar_one()
    listing = (await db.get(AuctionListing, appraisal.auction_listing_id)
               if appraisal.auction_listing_id else None)
    fee_bands = await _fee_bands_for(db, listing)

    risk_inputs = derive_risk_inputs(appraisal, vehicle, listing, dealership)

    costs = [
        {
            "name": c.name,
            "category": c.category,
            "estimated_amount": c.estimated_amount,
            "minimum_amount": c.minimum_amount,
            "maximum_amount": c.maximum_amount,
        }
        for c in appraisal.cost_items
    ]

    result = evaluate(
        expected_retail=appraisal.expected_retail_price,
        conservative_retail=appraisal.conservative_retail_price,
        optimistic_retail=appraisal.optimistic_retail_price,
        expected_discount=appraisal.expected_negotiated_discount,
        costs=costs,
        fee_bands=fee_bands,
        target_profit=appraisal.target_profit,
        risk_reserve=appraisal.risk_reserve,
        mandatory_min_reserve=dealership.mandatory_min_risk_reserve,
        min_roi=appraisal.desired_roi,
        vat_rate=dealership.vat_rate,
        current_bid=appraisal.current_bid,
        guide_price=(listing.guide_price if listing else None),
        estimated_days_to_sell=appraisal.estimated_days_to_sell,
        pricing_confidence=appraisal.pricing_confidence,
        max_acceptable_pessimistic_loss=dealership.max_acceptable_pessimistic_loss,
        risk_inputs=risk_inputs,
        risk_weights=dealership.risk_weights or None,
    )

    # Persist cached outputs.
    calc = result["calculation"]
    rec = result["recommendation"]
    risk = result["risk"]

    appraisal.recommendation = rec["decision"]
    appraisal.confidence_score = rec["confidence"]
    appraisal.risk_level = risk["level"]
    appraisal.result_snapshot = result
    if calc:
        appraisal.safe_max_bid = to_decimal(calc["safe_max_bid"])
        appraisal.absolute_max_bid = to_decimal(calc["absolute_max_bid"])
        appraisal.break_even_bid = to_decimal(calc["break_even_bid"])
        appraisal.expected_profit = to_decimal(calc["expected_profit"])
        appraisal.pessimistic_profit = to_decimal(calc["pessimistic_profit"])
        appraisal.optimistic_profit = to_decimal(calc["optimistic_profit"])
        appraisal.expected_roi = (to_decimal(calc["roi_on_cost"])
                                  if calc["roi_on_cost"] is not None else None)

    # Upsert risk assessment row.
    existing = (await db.execute(
        select(RiskAssessment).where(RiskAssessment.appraisal_id == appraisal.id)
    )).scalar_one_or_none()
    if existing is None:
        existing = RiskAssessment(appraisal_id=appraisal.id)
        db.add(existing)
    existing.scores = risk["scores"]
    existing.weighted_total = risk["weighted_total"]
    existing.risk_level = risk["level"]
    existing.explanations = risk["explanations"]
    existing.warning_flags = risk["warning_flags"]
    existing.critical_flags = risk["critical_flags"]
    existing.suggested_risk_reserve = to_decimal(risk["suggested_risk_reserve"])

    await db.flush()
    return result

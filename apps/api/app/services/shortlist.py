"""Scan-and-shortlist service.

Runs every auction listing in the dealership's catalogue through the calculation, risk and
recommendation engines and returns a ranked shortlist of cars worth bidding on. Works on any
listings in the database regardless of how they arrived (manual entry, CSV import, or — once a
licensed feed/agreement exists — an official auctioneer connector).

For listings that have not yet been fully appraised, a *conservative automated estimate* of the
retail values and preparation costs is used so a raw catalogue can still be scored. Those figures
are clearly labelled ``estimate_source = "AUTOMATED_ESTIMATE"`` and are a starting point for a
proper appraisal, never a final answer.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..calculations.money import to_decimal
from ..models.catalogue import AuctionHouse, AuctionListing, Vehicle
from ..models.organisation import Dealership
from .evaluation import evaluate
from .risk import RiskInputs

DEFAULT_ACCEPTED = {"STRONG_BUY", "BUY"}
RANK = {"STRONG_BUY": 0, "BUY": 1, "CONSIDER": 2, "HIGH_RISK": 3, "PASS": 4, "INCOMPLETE_DATA": 5}


def _estimate_retails(listing: AuctionListing) -> tuple[Decimal, Decimal, Decimal] | None:
    """Best-effort retail trio from whatever valuation data the listing already carries."""
    expected = listing.estimated_retail or listing.cap_clean
    conservative = listing.cap_average or listing.cap_below or expected
    if expected is None or conservative is None:
        return None
    expected = to_decimal(expected)
    conservative = to_decimal(conservative)
    optimistic = to_decimal(listing.cap_clean or expected) * Decimal("1.05")
    if optimistic < expected:
        optimistic = expected * Decimal("1.05")
    return expected, conservative, optimistic


def _auto_costs(listing: AuctionListing, house: AuctionHouse | None) -> list[dict[str, Any]]:
    """A conservative default preparation estimate, scaled by condition and runner status."""
    transport = to_decimal(house.default_transport_estimate) if house else Decimal("160")
    costs = [
        {"name": "Preparation service (estimate)", "category": "SERVICE",
         "estimated_amount": "250", "minimum_amount": "200", "maximum_amount": "350"},
        {"name": "Valeting (estimate)", "category": "VALETING",
         "estimated_amount": "110", "minimum_amount": "90", "maximum_amount": "160"},
        {"name": "Transport (estimate)", "category": "TRANSPORT",
         "estimated_amount": str(transport), "minimum_amount": str(transport),
         "maximum_amount": str(transport + Decimal("60"))},
    ]
    grade = listing.condition_grade or 2
    if grade >= 4:
        costs.append({"name": "Repairs — poor condition (estimate)", "category": "MECHANICAL",
                      "estimated_amount": "700", "minimum_amount": "400", "maximum_amount": "1400"})
    elif grade == 3:
        costs.append({"name": "Repairs — fair condition (estimate)", "category": "MECHANICAL",
                      "estimated_amount": "350", "minimum_amount": "200", "maximum_amount": "700"})
    if (listing.runner_status or "").upper() == "NON_RUNNER":
        costs.append({"name": "Non-runner recovery & repair (estimate)", "category": "MECHANICAL",
                      "estimated_amount": "1400", "minimum_amount": "600", "maximum_amount": "2600"})
    return costs


def _risk_inputs(vehicle: Vehicle, listing: AuctionListing, dealership: Dealership) -> RiskInputs:
    h = vehicle.history
    return RiskInputs(
        category_marker=vehicle.category_marker,
        stolen_marker=bool(h and h.stolen_marker),
        outstanding_finance=bool(h and h.finance_marker),
        write_off_marker=bool(h and h.write_off_marker),
        mileage_discrepancy=bool(h and h.mileage_discrepancy),
        imported=vehicle.imported,
        keeper_changes=(h.keeper_changes if h else (vehicle.previous_keepers or 0)),
        mot_fail_count=(h.mot_fail_count if h else 0),
        dangerous_defect_count=(h.dangerous_defect_count if h else 0),
        non_runner=((listing.runner_status or "").upper() == "NON_RUNNER"),
        condition_grade=listing.condition_grade,
        missing_service_history=bool(h and (h.service_history_status or "").upper() == "NONE"),
        one_key_only=(vehicle.number_of_keys == 1),
        mileage=vehicle.mileage,
        allow_category_n=dealership.allow_category_n,
        allow_category_s=dealership.allow_category_s,
    )


def _fee_bands(house: AuctionHouse | None) -> list[dict[str, Any]]:
    if house is None:
        return []
    return [
        {"fixed_fee": b.fixed_fee, "percentage": b.percentage, "minimum_fee": b.minimum_fee,
         "maximum_fee": b.maximum_fee, "lower_bound": b.lower_bound, "upper_bound": b.upper_bound,
         "vat_applicable": b.vat_applicable, "stated_inclusive": b.stated_inclusive}
        for b in house.fee_bands
    ]


async def scan(
    db: AsyncSession,
    dealership_id: int,
    *,
    accepted: set[str] | None = None,
    auction_house_id: int | None = None,
    due_on: date | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    accepted = accepted or DEFAULT_ACCEPTED
    dealership = await db.get(Dealership, dealership_id)

    stmt = (
        select(AuctionListing)
        .options(
            selectinload(AuctionListing.vehicle).selectinload(Vehicle.history),
            selectinload(AuctionListing.auction_house).selectinload(AuctionHouse.fee_bands),
        )
        .where(
            AuctionListing.dealership_id == dealership_id,
            AuctionListing.listing_status.in_(["UPCOMING", "LIVE"]),
        )
    )
    if auction_house_id:
        stmt = stmt.where(AuctionListing.auction_house_id == auction_house_id)
    if due_on is not None:
        # Auctions taking place on the given calendar day (UTC).
        day_start = datetime.combine(due_on, time.min, tzinfo=timezone.utc)
        day_end = datetime.combine(due_on, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(
            AuctionListing.auction_datetime >= day_start,
            AuctionListing.auction_datetime <= day_end,
        )

    listings = (await db.execute(stmt)).scalars().all()

    candidates: list[dict[str, Any]] = []
    scanned = 0
    skipped_no_valuation = 0

    for listing in listings:
        retails = _estimate_retails(listing)
        if retails is None:
            skipped_no_valuation += 1
            continue
        scanned += 1
        expected, conservative, optimistic = retails
        vehicle = listing.vehicle
        house = listing.auction_house

        result = evaluate(
            expected_retail=expected,
            conservative_retail=conservative,
            optimistic_retail=optimistic,
            expected_discount=Decimal("150"),
            costs=_auto_costs(listing, house),
            fee_bands=_fee_bands(house),
            target_profit=dealership.default_target_profit,
            risk_reserve=dealership.default_risk_reserve,
            mandatory_min_reserve=dealership.mandatory_min_risk_reserve,
            min_roi=dealership.default_min_roi,
            vat_rate=dealership.vat_rate,
            current_bid=listing.guide_price,
            guide_price=listing.guide_price,
            estimated_days_to_sell=45,
            pricing_confidence="MEDIUM",
            max_acceptable_pessimistic_loss=dealership.max_acceptable_pessimistic_loss,
            risk_inputs=_risk_inputs(vehicle, listing, dealership),
            risk_weights=dealership.risk_weights or None,
        )
        calc = result["calculation"]
        rec = result["recommendation"]
        candidates.append({
            "listing_id": listing.id,
            "vehicle_id": vehicle.id,
            "make": vehicle.make,
            "model": vehicle.model,
            "derivative": vehicle.derivative,
            "registration": vehicle.registration,
            "lot_number": listing.lot_number,
            "auction_house": house.name if house else None,
            "auction_datetime": (listing.auction_datetime.isoformat()
                                 if listing.auction_datetime else None),
            "guide_price": str(listing.guide_price) if listing.guide_price is not None else None,
            "decision": rec["decision"],
            "risk_level": result["risk"]["level"],
            "safe_max_bid": calc["safe_max_bid"] if calc else None,
            "absolute_max_bid": calc["absolute_max_bid"] if calc else None,
            "expected_profit": calc["expected_profit"] if calc else None,
            "pessimistic_profit": calc["pessimistic_profit"] if calc else None,
            "roi_on_cost": calc["roi_on_cost"] if calc else None,
            "headline_reason": rec["reasons"][0] if rec["reasons"] else "",
            "estimate_source": "AUTOMATED_ESTIMATE",
        })

    shortlist = [c for c in candidates if c["decision"] in accepted]
    shortlist.sort(key=lambda c: (RANK.get(c["decision"], 9), -float(c["expected_profit"] or 0)))

    return {
        "scanned": scanned,
        "skipped_no_valuation": skipped_no_valuation,
        "shortlisted": len(shortlist),
        "accepted_decisions": sorted(accepted),
        "due_on": due_on.isoformat() if due_on else None,
        "candidates": shortlist[:limit],
        "note": (
            "Automated first-pass estimate using listing valuation data and default preparation "
            "costs. Complete a full appraisal before bidding. Figures are estimates, not guarantees."
        ),
    }

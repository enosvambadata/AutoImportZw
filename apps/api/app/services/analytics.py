"""Dashboard and analytics computations over persisted data.

Every figure is labelled as estimated, forecast or actual so the two are never conflated.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..calculations.money import money, ratio, safe_div, to_decimal
from ..models.appraisal import Appraisal
from ..models.trading import Purchase

BUY_DECISIONS = {"STRONG_BUY", "BUY"}


def _avg(values: list[Decimal]) -> Decimal | None:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return money(sum(vals) / len(vals))


async def dashboard(db: AsyncSession, dealership_id: int) -> dict:
    appraisals = (await db.execute(
        select(Appraisal).where(Appraisal.dealership_id == dealership_id)
    )).scalars().all()

    purchases = (await db.execute(
        select(Purchase).options(selectinload(Purchase.preparation_costs),
                                 selectinload(Purchase.sale))
        .where(Purchase.dealership_id == dealership_id)
    )).scalars().all()

    total_appraised = len(appraisals)
    strong_or_buy = sum(1 for a in appraisals if a.recommendation in BUY_DECISIONS)
    passed = sum(1 for a in appraisals if a.recommendation == "PASS"
                 or a.status == "PASSED")
    expected_profits = [to_decimal(a.expected_profit) for a in appraisals
                        if a.expected_profit is not None]

    # Actual profit from completed sales.
    actual_profits: list[Decimal] = []
    days_in_stock: list[int] = []
    capital_required = Decimal("0")
    for p in purchases:
        prep = sum((to_decimal(c.actual_amount) for c in p.preparation_costs), Decimal("0"))
        invested = to_decimal(p.actual_hammer_price) + to_decimal(p.actual_auction_fees) \
            + to_decimal(p.actual_transport_cost) + prep
        if p.sale is None:
            capital_required += invested  # still in stock
        else:
            if p.sale.net_contribution is not None:
                actual_profits.append(to_decimal(p.sale.net_contribution))
            if p.sale.days_in_stock is not None:
                days_in_stock.append(p.sale.days_in_stock)

    conversion = safe_div(len(purchases), total_appraised)

    return {
        "vehicles_appraised": total_appraised,
        "strong_buys_and_buys": strong_or_buy,
        "passed_vehicles": passed,
        "average_expected_profit": str(_avg(expected_profits)) if expected_profits else None,
        "average_actual_profit": str(_avg(actual_profits)) if actual_profits else None,
        "average_days_in_stock": (round(sum(days_in_stock) / len(days_in_stock))
                                  if days_in_stock else None),
        "estimated_capital_required": str(money(capital_required)),
        "profit_forecast": str(money(sum(expected_profits))) if expected_profits else "0.00",
        "appraisal_to_purchase_conversion": (str(ratio(conversion)) if conversion is not None
                                             else "0"),
        "recent_appraisals": [
            {
                "id": a.id,
                "recommendation": a.recommendation,
                "expected_profit": str(a.expected_profit) if a.expected_profit else None,
                "risk_level": a.risk_level,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in sorted(appraisals, key=lambda x: x.created_at, reverse=True)[:8]
        ],
        "vehicles_requiring_action": [
            {"id": a.id, "recommendation": a.recommendation, "status": a.status}
            for a in appraisals
            if a.status == "DRAFT" or a.recommendation == "CONSIDER"
        ][:8],
    }


async def analytics(db: AsyncSession, dealership_id: int) -> dict:
    purchases = (await db.execute(
        select(Purchase)
        .options(selectinload(Purchase.preparation_costs),
                 selectinload(Purchase.sale),
                 selectinload(Purchase.appraisal).selectinload(Appraisal.vehicle))
        .where(Purchase.dealership_id == dealership_id)
    )).scalars().all()
    appraisals = (await db.execute(
        select(Appraisal).where(Appraisal.dealership_id == dealership_id)
    )).scalars().all()

    roi_by_make: dict[str, list[Decimal]] = defaultdict(list)
    prep_variance: list[Decimal] = []
    estimated_vs_actual = []
    capital_in_stock = Decimal("0")
    stock_ageing = []

    for p in purchases:
        prep = sum((to_decimal(c.actual_amount) for c in p.preparation_costs), Decimal("0"))
        invested = to_decimal(p.actual_hammer_price) + to_decimal(p.actual_auction_fees) \
            + to_decimal(p.actual_transport_cost) + prep
        appr = p.appraisal
        make = appr.vehicle.make if appr and appr.vehicle else "Unknown"

        # Estimated prep = sum of appraisal cost items that are prep-like (exclude fees).
        est_prep = Decimal("0")
        if appr:
            est_prep = sum(
                (to_decimal(c.estimated_amount) for c in appr.cost_items
                 if c.category not in ("AUCTION_FEE", "FEE_VAT")),
                Decimal("0"),
            )
        prep_variance.append(money(prep - est_prep))

        if p.sale and p.sale.net_contribution is not None:
            actual_profit = to_decimal(p.sale.net_contribution)
            r = safe_div(actual_profit, invested)
            if r is not None:
                roi_by_make[make].append(to_decimal(r))
            estimated_vs_actual.append({
                "purchase_id": p.id,
                "make": make,
                "estimated_profit": str(appr.expected_profit) if appr and appr.expected_profit else None,
                "actual_profit": str(actual_profit),
                "estimated_prep": str(money(est_prep)),
                "actual_prep": str(money(prep)),
            })
        else:
            capital_in_stock += invested
            stock_ageing.append({"purchase_id": p.id, "make": make,
                                 "status": p.preparation_status})

    pass_count = sum(1 for a in appraisals if a.recommendation == "PASS")
    pass_rate = safe_div(pass_count, len(appraisals)) if appraisals else None

    return {
        "roi_by_make": {k: str(_avg(v)) for k, v in roi_by_make.items() if _avg(v) is not None},
        "average_prep_variance": str(_avg(prep_variance)) if prep_variance else None,
        "estimated_vs_actual": estimated_vs_actual,
        "pass_rate": str(ratio(pass_rate)) if pass_rate is not None else None,
        "purchase_conversion_rate": (str(ratio(safe_div(len(purchases), len(appraisals))))
                                     if appraisals else None),
        "capital_tied_up_in_stock": str(money(capital_in_stock)),
        "stock_ageing": stock_ageing,
        "note": "ROI figures use actual net contribution / actual cash invested where sold.",
    }

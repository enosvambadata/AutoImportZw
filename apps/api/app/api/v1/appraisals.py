"""Appraisals: CRUD, calculation preview, recompute, cost items and comparables."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...models.appraisal import Appraisal, CostItem, MarketComparable
from ...models.catalogue import AuctionFeeBand, AuctionListing, Vehicle
from ...models.enums import AppraisalStatus, AuditAction
from ...models.organisation import Dealership, User
from ...schemas.appraisal import (
    AppraisalCreate,
    AppraisalOut,
    AppraisalUpdate,
    EvaluationResponse,
    PreviewRequest,
)
from ...schemas.common import Message, Page
from ...services import audit
from ...services.appraisal_service import compute_and_store
from ...services.evaluation import evaluate
from ...services.risk import RiskInputs

router = APIRouter(prefix="/appraisals", tags=["appraisals"])

_LOAD = (
    selectinload(Appraisal.cost_items),
    selectinload(Appraisal.comparables),
    selectinload(Appraisal.risk_assessment),
    selectinload(Appraisal.vehicle),
)


async def _load(db: AsyncSession, appraisal_id: int, dealership_id: int) -> Appraisal:
    appraisal = (await db.execute(
        select(Appraisal).options(*_LOAD)
        .where(Appraisal.id == appraisal_id, Appraisal.dealership_id == dealership_id)
    )).scalar_one_or_none()
    if appraisal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appraisal not found")
    return appraisal


@router.post("/preview", response_model=EvaluationResponse)
async def preview(
    payload: PreviewRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stateless calculation preview — the single source of truth for the wizard's live figures."""
    dealership = await db.get(Dealership, user.dealership_id)

    fee_bands: list[dict] = [b.model_dump() for b in payload.fee_bands]
    if not fee_bands and payload.auction_house_id:
        rows = (await db.execute(
            select(AuctionFeeBand).where(
                AuctionFeeBand.auction_house_id == payload.auction_house_id)
        )).scalars().all()
        fee_bands = [
            {"fixed_fee": b.fixed_fee, "percentage": b.percentage, "minimum_fee": b.minimum_fee,
             "maximum_fee": b.maximum_fee, "lower_bound": b.lower_bound,
             "upper_bound": b.upper_bound, "vat_applicable": b.vat_applicable,
             "stated_inclusive": b.stated_inclusive}
            for b in rows
        ]

    risk_inputs = RiskInputs(
        allow_category_n=dealership.allow_category_n,
        allow_category_s=dealership.allow_category_s,
    )
    if payload.risk_signals:
        for key, value in payload.risk_signals.model_dump().items():
            setattr(risk_inputs, key, value)

    result = evaluate(
        expected_retail=payload.expected_retail_price,
        conservative_retail=payload.conservative_retail_price,
        optimistic_retail=payload.optimistic_retail_price,
        expected_discount=payload.expected_negotiated_discount,
        costs=[c.model_dump() for c in payload.cost_items],
        fee_bands=fee_bands,
        target_profit=payload.target_profit,
        risk_reserve=payload.risk_reserve,
        mandatory_min_reserve=dealership.mandatory_min_risk_reserve,
        min_roi=payload.desired_roi,
        vat_rate=dealership.vat_rate,
        current_bid=payload.current_bid,
        guide_price=payload.guide_price,
        estimated_days_to_sell=payload.estimated_days_to_sell,
        pricing_confidence=payload.pricing_confidence,
        max_acceptable_pessimistic_loss=dealership.max_acceptable_pessimistic_loss,
        risk_inputs=risk_inputs,
        risk_weights=dealership.risk_weights or None,
    )
    return result


@router.get("", response_model=Page[AppraisalOut])
async def list_appraisals(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    recommendation: str | None = None,
    risk_level: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = select(Appraisal).where(Appraisal.dealership_id == user.dealership_id)
    if recommendation:
        stmt = stmt.where(Appraisal.recommendation == recommendation)
    if risk_level:
        stmt = stmt.where(Appraisal.risk_level == risk_level)
    if status_filter:
        stmt = stmt.where(Appraisal.status == status_filter)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(
        stmt.options(*_LOAD).order_by(Appraisal.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return Page(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{appraisal_id}", response_model=AppraisalOut)
async def get_appraisal(appraisal_id: int, user: CurrentUser,
                       db: Annotated[AsyncSession, Depends(get_db)]):
    return await _load(db, appraisal_id, user.dealership_id)


def _apply_children(appraisal: Appraisal, payload) -> None:
    if payload.cost_items is not None:
        appraisal.cost_items = [CostItem(**c.model_dump()) for c in payload.cost_items]
    if payload.comparables is not None:
        appraisal.comparables = [MarketComparable(**c.model_dump()) for c in payload.comparables]


@router.post("", response_model=AppraisalOut, status_code=status.HTTP_201_CREATED)
async def create_appraisal(
    payload: AppraisalCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    vehicle = await db.get(Vehicle, payload.vehicle_id)
    if vehicle is None or vehicle.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    if payload.auction_listing_id:
        listing = await db.get(AuctionListing, payload.auction_listing_id)
        if listing is None or listing.dealership_id != buyer.dealership_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")

    appraisal = Appraisal(
        dealership_id=buyer.dealership_id,
        appraiser_id=buyer.id,
        **payload.model_dump(exclude={"cost_items", "comparables", "risk_signals", "status"}),
        status=payload.status.value,
    )
    appraisal.cost_items = [CostItem(**c.model_dump()) for c in payload.cost_items]
    appraisal.comparables = [MarketComparable(**c.model_dump()) for c in payload.comparables]
    db.add(appraisal)
    await db.flush()
    await compute_and_store(db, appraisal)
    await audit.record(db, actor=buyer, action=AuditAction.APPRAISAL_CREATED, entity="appraisal",
                       entity_id=appraisal.id, new_value={"recommendation": appraisal.recommendation})
    return await _load(db, appraisal.id, buyer.dealership_id)


@router.put("/{appraisal_id}", response_model=AppraisalOut)
async def update_appraisal(
    appraisal_id: int,
    payload: AppraisalUpdate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    appraisal = await _load(db, appraisal_id, buyer.dealership_id)
    old = {"recommendation": appraisal.recommendation,
           "expected_profit": str(appraisal.expected_profit)}
    for key, value in payload.model_dump(
            exclude={"cost_items", "comparables", "risk_signals", "status"},
            exclude_unset=True).items():
        setattr(appraisal, key, value)
    if payload.status is not None:
        appraisal.status = payload.status.value
    _apply_children(appraisal, payload)
    await db.flush()
    await compute_and_store(db, appraisal)
    await audit.record(db, actor=buyer, action=AuditAction.APPRAISAL_UPDATED, entity="appraisal",
                       entity_id=appraisal.id, old_value=old,
                       new_value={"recommendation": appraisal.recommendation,
                                  "expected_profit": str(appraisal.expected_profit)})
    return await _load(db, appraisal.id, buyer.dealership_id)


@router.post("/{appraisal_id}/recompute", response_model=AppraisalOut)
async def recompute(appraisal_id: int, buyer: Annotated[User, Depends(require_buyer)],
                   db: Annotated[AsyncSession, Depends(get_db)]):
    appraisal = await _load(db, appraisal_id, buyer.dealership_id)
    await compute_and_store(db, appraisal)
    await audit.record(db, actor=buyer, action=AuditAction.RECOMMENDATION_RECALCULATED,
                       entity="appraisal", entity_id=appraisal.id)
    return await _load(db, appraisal.id, buyer.dealership_id)


@router.post("/{appraisal_id}/duplicate", response_model=AppraisalOut,
             status_code=status.HTTP_201_CREATED)
async def duplicate(appraisal_id: int, buyer: Annotated[User, Depends(require_buyer)],
                   db: Annotated[AsyncSession, Depends(get_db)]):
    src = await _load(db, appraisal_id, buyer.dealership_id)
    clone = Appraisal(
        dealership_id=src.dealership_id, vehicle_id=src.vehicle_id,
        auction_listing_id=src.auction_listing_id, appraiser_id=buyer.id,
        status=AppraisalStatus.DRAFT.value,
        expected_retail_price=src.expected_retail_price,
        conservative_retail_price=src.conservative_retail_price,
        optimistic_retail_price=src.optimistic_retail_price,
        expected_negotiated_discount=src.expected_negotiated_discount,
        pricing_confidence=src.pricing_confidence, target_profit=src.target_profit,
        risk_reserve=src.risk_reserve, desired_roi=src.desired_roi,
        estimated_days_to_sell=src.estimated_days_to_sell, current_bid=src.current_bid,
    )
    clone.cost_items = [CostItem(name=c.name, category=c.category,
                                 estimated_amount=c.estimated_amount,
                                 minimum_amount=c.minimum_amount, maximum_amount=c.maximum_amount,
                                 vat_treatment=c.vat_treatment, certainty=c.certainty)
                        for c in src.cost_items]
    db.add(clone)
    await db.flush()
    await compute_and_store(db, clone)
    return await _load(db, clone.id, buyer.dealership_id)


@router.post("/{appraisal_id}/pass", response_model=Message)
async def mark_passed(appraisal_id: int, buyer: Annotated[User, Depends(require_buyer)],
                     db: Annotated[AsyncSession, Depends(get_db)]):
    appraisal = await _load(db, appraisal_id, buyer.dealership_id)
    appraisal.status = AppraisalStatus.PASSED.value
    await db.flush()
    return Message(message="Appraisal marked as passed")

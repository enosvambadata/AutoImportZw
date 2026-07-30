"""Purchases and actual preparation costs."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...calculations.money import money, to_decimal
from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...models.appraisal import Appraisal
from ...models.enums import AppraisalStatus, AuditAction
from ...models.organisation import User
from ...models.trading import PreparationCost, Purchase
from ...schemas.trading import (
    PreparationCostCreate,
    PurchaseCreate,
    PurchaseOut,
    PurchaseUpdate,
)
from ...services import audit

router = APIRouter(prefix="/purchases", tags=["purchases"])


def _augment(purchase: Purchase) -> Purchase:
    prep = sum((to_decimal(c.actual_amount) for c in purchase.preparation_costs), Decimal("0"))
    purchase.total_preparation_cost = money(prep)
    purchase.total_invested = money(
        to_decimal(purchase.actual_hammer_price) + to_decimal(purchase.actual_auction_fees)
        + to_decimal(purchase.actual_transport_cost) + prep
    )
    return purchase


async def _load(db: AsyncSession, purchase_id: int, dealership_id: int) -> Purchase:
    purchase = (await db.execute(
        select(Purchase).options(selectinload(Purchase.preparation_costs))
        .where(Purchase.id == purchase_id, Purchase.dealership_id == dealership_id)
    )).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    return purchase


@router.get("", response_model=list[PurchaseOut])
async def list_purchases(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(Purchase).options(selectinload(Purchase.preparation_costs))
        .where(Purchase.dealership_id == user.dealership_id).order_by(Purchase.id.desc())
    )).scalars().all()
    return [_augment(p) for p in rows]


@router.get("/{purchase_id}", response_model=PurchaseOut)
async def get_purchase(purchase_id: int, user: CurrentUser,
                      db: Annotated[AsyncSession, Depends(get_db)]):
    return _augment(await _load(db, purchase_id, user.dealership_id))


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not payload.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Purchase must be explicitly confirmed (confirm=true)")
    appraisal = await db.get(Appraisal, payload.appraisal_id)
    if appraisal is None or appraisal.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appraisal not found")
    existing = (await db.execute(
        select(Purchase).where(Purchase.appraisal_id == appraisal.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This appraisal is already a purchase")

    purchase = Purchase(
        dealership_id=buyer.dealership_id,
        purchased_by_id=buyer.id,
        **payload.model_dump(exclude={"confirm"}),
    )
    db.add(purchase)
    appraisal.status = AppraisalStatus.PURCHASED.value
    await db.flush()
    await db.refresh(purchase, attribute_names=["preparation_costs"])
    await audit.record(db, actor=buyer, action=AuditAction.VEHICLE_PURCHASED, entity="purchase",
                       entity_id=purchase.id,
                       new_value={"hammer": str(purchase.actual_hammer_price)})
    return _augment(purchase)


@router.patch("/{purchase_id}", response_model=PurchaseOut)
async def update_purchase(
    purchase_id: int,
    payload: PurchaseUpdate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    purchase = await _load(db, purchase_id, buyer.dealership_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(purchase, key, value)
    await db.flush()
    return _augment(purchase)


@router.post("/{purchase_id}/preparation-costs", response_model=PurchaseOut,
             status_code=status.HTTP_201_CREATED)
async def add_prep_cost(
    purchase_id: int,
    payload: PreparationCostCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    purchase = await _load(db, purchase_id, buyer.dealership_id)
    purchase.preparation_costs.append(PreparationCost(**payload.model_dump()))
    await db.flush()
    await db.refresh(purchase, attribute_names=["preparation_costs"])
    await audit.record(db, actor=buyer, action=AuditAction.COST_CHANGED, entity="purchase",
                       entity_id=purchase.id, new_value={"prep_cost": str(payload.actual_amount)})
    return _augment(purchase)


@router.delete("/{purchase_id}/preparation-costs/{cost_id}", response_model=PurchaseOut)
async def delete_prep_cost(
    purchase_id: int,
    cost_id: int,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    purchase = await _load(db, purchase_id, buyer.dealership_id)
    cost = await db.get(PreparationCost, cost_id)
    if cost is None or cost.purchase_id != purchase.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Preparation cost not found")
    await db.delete(cost)
    await db.flush()
    await db.refresh(purchase, attribute_names=["preparation_costs"])
    return _augment(purchase)

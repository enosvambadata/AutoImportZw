"""Sales completion with actual profit calculation."""

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
from ...models.enums import AuditAction, PreparationStatus
from ...models.organisation import User
from ...models.trading import Purchase, Sale
from ...schemas.trading import SaleCreate, SaleOut
from ...services import audit

router = APIRouter(prefix="/sales", tags=["sales"])


def _compute(sale: Sale, purchase: Purchase) -> None:
    prep = sum((to_decimal(c.actual_amount) for c in purchase.preparation_costs), Decimal("0"))
    invested = (to_decimal(purchase.actual_hammer_price) + to_decimal(purchase.actual_auction_fees)
                + to_decimal(purchase.actual_transport_cost) + prep)

    gross = to_decimal(sale.final_selling_price) - invested
    net = (to_decimal(sale.final_selling_price)
           - to_decimal(sale.customer_discount)
           + to_decimal(sale.part_exchange_adjustment)
           + to_decimal(sale.other_income)
           + to_decimal(sale.finance_commission)
           - invested
           - to_decimal(sale.warranty_cost)
           - to_decimal(sale.advertising_cost)
           - to_decimal(sale.other_costs))
    sale.gross_profit = money(gross)
    sale.net_contribution = money(net)
    sale.days_in_stock = (sale.sale_date - purchase.purchase_date).days


@router.get("", response_model=list[SaleOut])
async def list_sales(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(Sale).where(Sale.dealership_id == user.dealership_id).order_by(Sale.id.desc())
    )).scalars().all()
    return rows


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
async def create_sale(
    payload: SaleCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    purchase = (await db.execute(
        select(Purchase).options(selectinload(Purchase.preparation_costs))
        .where(Purchase.id == payload.purchase_id,
               Purchase.dealership_id == buyer.dealership_id)
    )).scalar_one_or_none()
    if purchase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    existing = (await db.execute(
        select(Sale).where(Sale.purchase_id == purchase.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This purchase is already sold")
    if payload.sale_date < purchase.purchase_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Sale date cannot be before the purchase date")

    sale = Sale(dealership_id=buyer.dealership_id, **payload.model_dump())
    _compute(sale, purchase)
    purchase.preparation_status = PreparationStatus.SOLD.value
    db.add(sale)
    await db.flush()
    await audit.record(db, actor=buyer, action=AuditAction.VEHICLE_SOLD, entity="sale",
                       entity_id=sale.id,
                       new_value={"net_contribution": str(sale.net_contribution),
                                  "days_in_stock": sale.days_in_stock})
    return sale

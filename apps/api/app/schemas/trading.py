"""Purchase, preparation cost and sale schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from .common import ORMModel


class PreparationCostBase(BaseModel):
    category: str = "OTHER"
    description: str = Field(min_length=1, max_length=160)
    actual_amount: Decimal = Field(default=Decimal("0"), ge=0)
    vat_treatment: str = "NONE"
    incurred_on: date | None = None
    supplier: str | None = None


class PreparationCostCreate(PreparationCostBase):
    pass


class PreparationCostOut(PreparationCostBase, ORMModel):
    id: int
    purchase_id: int


class PurchaseCreate(BaseModel):
    appraisal_id: int
    actual_hammer_price: Decimal = Field(ge=0)
    actual_auction_fees: Decimal = Field(default=Decimal("0"), ge=0)
    actual_transport_cost: Decimal = Field(default=Decimal("0"), ge=0)
    purchase_date: date
    funding_source: str | None = None
    stock_number: str | None = None
    notes: str | None = None
    confirm: bool = Field(default=False, description="Must be true to convert to a purchase")


class PurchaseUpdate(BaseModel):
    actual_auction_fees: Decimal | None = None
    actual_transport_cost: Decimal | None = None
    funding_source: str | None = None
    stock_number: str | None = None
    preparation_status: str | None = None
    notes: str | None = None


class PurchaseOut(ORMModel):
    id: int
    dealership_id: int
    appraisal_id: int
    actual_hammer_price: Decimal
    actual_auction_fees: Decimal
    actual_transport_cost: Decimal
    purchase_date: date
    funding_source: str | None
    stock_number: str | None
    purchased_by_id: int
    preparation_status: str
    notes: str | None
    created_at: datetime
    preparation_costs: list[PreparationCostOut] = Field(default_factory=list)
    total_preparation_cost: Decimal | None = None
    total_invested: Decimal | None = None


class SaleCreate(BaseModel):
    purchase_id: int
    advertised_price: Decimal | None = Field(default=None, ge=0)
    final_selling_price: Decimal = Field(ge=0)
    sale_date: date
    customer_discount: Decimal = Field(default=Decimal("0"), ge=0)
    warranty_cost: Decimal = Field(default=Decimal("0"), ge=0)
    advertising_cost: Decimal = Field(default=Decimal("0"), ge=0)
    finance_commission: Decimal = Field(default=Decimal("0"), ge=0)
    part_exchange_adjustment: Decimal = Decimal("0")
    other_income: Decimal = Field(default=Decimal("0"), ge=0)
    other_costs: Decimal = Field(default=Decimal("0"), ge=0)


class SaleOut(ORMModel):
    id: int
    dealership_id: int
    purchase_id: int
    advertised_price: Decimal | None
    final_selling_price: Decimal
    sale_date: date
    customer_discount: Decimal
    warranty_cost: Decimal
    advertising_cost: Decimal
    finance_commission: Decimal
    part_exchange_adjustment: Decimal
    other_income: Decimal
    other_costs: Decimal
    gross_profit: Decimal | None
    net_contribution: Decimal | None
    days_in_stock: int | None

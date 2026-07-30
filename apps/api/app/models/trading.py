"""Purchases, preparation costs and sales (actuals)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, IntPKMixin, TimestampMixin


class Purchase(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "purchases"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"), unique=True, index=True)
    actual_hammer_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    actual_auction_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    actual_transport_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    purchase_date: Mapped[date] = mapped_column(Date)
    funding_source: Mapped[str | None] = mapped_column(String(60))
    stock_number: Mapped[str | None] = mapped_column(String(40))
    purchased_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    preparation_status: Mapped[str] = mapped_column(String(20), default="AWAITING")
    notes: Mapped[str | None] = mapped_column(Text)

    appraisal: Mapped["Appraisal"] = relationship()  # noqa: F821, UP037 (cross-module registry ref)
    preparation_costs: Mapped[list[PreparationCost]] = relationship(
        back_populates="purchase", cascade="all, delete-orphan")
    sale: Mapped[Sale | None] = relationship(
        back_populates="purchase", uselist=False, cascade="all, delete-orphan")


class PreparationCost(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "preparation_costs"

    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), index=True)
    category: Mapped[str] = mapped_column(String(30), default="OTHER")
    description: Mapped[str] = mapped_column(String(160))
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    vat_treatment: Mapped[str] = mapped_column(String(20), default="NONE")
    incurred_on: Mapped[date | None] = mapped_column(Date)
    supplier: Mapped[str | None] = mapped_column(String(120))

    purchase: Mapped[Purchase] = relationship(back_populates="preparation_costs")


class Sale(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "sales"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), unique=True, index=True)
    advertised_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    final_selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sale_date: Mapped[date] = mapped_column(Date)
    customer_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    warranty_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    advertising_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    finance_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    part_exchange_adjustment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_income: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    other_costs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    gross_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    net_contribution: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    days_in_stock: Mapped[int | None] = mapped_column(Integer)

    purchase: Mapped[Purchase] = relationship(back_populates="sale")

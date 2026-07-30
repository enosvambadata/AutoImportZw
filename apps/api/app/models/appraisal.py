"""Appraisal, cost items, risk assessment and market comparables."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, IntPKMixin, TimestampMixin


class Appraisal(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "appraisals"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    auction_listing_id: Mapped[int | None] = mapped_column(
        ForeignKey("auction_listings.id"), index=True)
    appraiser_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")

    # Valuation inputs
    expected_retail_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    conservative_retail_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    optimistic_retail_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_negotiated_discount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"))
    pricing_confidence: Mapped[str] = mapped_column(String(10), default="MEDIUM")

    # Policy inputs
    target_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1200"))
    risk_reserve: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("300"))
    desired_roi: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.15"))
    estimated_days_to_sell: Mapped[int] = mapped_column(Integer, default=45)
    current_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    # Cached outputs (recomputed on write; API is still the source of truth)
    confidence_score: Mapped[str | None] = mapped_column(String(10))
    recommendation: Mapped[str | None] = mapped_column(String(20))
    safe_max_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    absolute_max_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    break_even_bid: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    pessimistic_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    optimistic_profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_roi: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    risk_level: Mapped[str | None] = mapped_column(String(20))
    result_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)

    vehicle: Mapped["Vehicle"] = relationship()  # noqa: F821, UP037 (cross-module registry ref)
    cost_items: Mapped[list[CostItem]] = relationship(
        back_populates="appraisal", cascade="all, delete-orphan")
    comparables: Mapped[list[MarketComparable]] = relationship(
        back_populates="appraisal", cascade="all, delete-orphan")
    risk_assessment: Mapped[RiskAssessment | None] = relationship(
        back_populates="appraisal", uselist=False, cascade="all, delete-orphan")


class CostItem(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "cost_items"

    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(30), default="OTHER")
    estimated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    minimum_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    maximum_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    vat_treatment: Mapped[str] = mapped_column(String(20), default="NONE")
    certainty: Mapped[str] = mapped_column(String(10), default="MEDIUM")
    notes: Mapped[str | None] = mapped_column(Text)

    appraisal: Mapped[Appraisal] = relationship(back_populates="cost_items")


class RiskAssessment(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "risk_assessments"

    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"), unique=True, index=True)
    scores: Mapped[dict] = mapped_column(JSON, default=dict)  # category -> 0-100
    weighted_total: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    explanations: Mapped[dict] = mapped_column(JSON, default=list)
    warning_flags: Mapped[dict] = mapped_column(JSON, default=list)
    critical_flags: Mapped[dict] = mapped_column(JSON, default=list)
    suggested_risk_reserve: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    appraisal: Mapped[Appraisal] = relationship(back_populates="risk_assessment")


class MarketComparable(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "market_comparables"

    appraisal_id: Mapped[int] = mapped_column(ForeignKey("appraisals.id"), index=True)
    source: Mapped[str] = mapped_column(String(40), default="MANUAL")
    listing_reference: Mapped[str | None] = mapped_column(String(80))
    asking_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    mileage: Mapped[int | None] = mapped_column(Integer)
    year: Mapped[int | None] = mapped_column(Integer)
    trim: Mapped[str | None] = mapped_column(String(120))
    distance_miles: Mapped[int | None] = mapped_column(Integer)
    seller_type: Mapped[str | None] = mapped_column(String(20))
    days_listed: Mapped[int | None] = mapped_column(Integer)
    price_change: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    url: Mapped[str | None] = mapped_column(String(255))
    captured_on: Mapped[date | None] = mapped_column()

    appraisal: Mapped[Appraisal] = relationship(back_populates="comparables")

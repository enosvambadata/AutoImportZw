"""Appraisal, cost item, comparable, risk and calculation-preview schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from ..models.enums import AppraisalStatus, Certainty, CostCategory
from .common import ORMModel


# ---- Cost items ----
class CostItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: CostCategory = CostCategory.OTHER
    estimated_amount: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_amount: Decimal | None = Field(default=None, ge=0)
    maximum_amount: Decimal | None = Field(default=None, ge=0)
    vat_treatment: str = "NONE"
    certainty: Certainty = Certainty.MEDIUM
    notes: str | None = None


class CostItemCreate(CostItemBase):
    pass


class CostItemOut(CostItemBase, ORMModel):
    id: int
    appraisal_id: int


# ---- Comparables ----
class ComparableBase(BaseModel):
    source: str = "MANUAL"
    listing_reference: str | None = None
    asking_price: Decimal | None = Field(default=None, ge=0)
    mileage: int | None = None
    year: int | None = None
    trim: str | None = None
    distance_miles: int | None = None
    seller_type: str | None = None
    days_listed: int | None = None
    price_change: Decimal | None = None
    url: str | None = None
    captured_on: date | None = None


class ComparableCreate(ComparableBase):
    pass


class ComparableOut(ComparableBase, ORMModel):
    id: int
    appraisal_id: int


# ---- Risk ----
class RiskAssessmentOut(ORMModel):
    id: int
    appraisal_id: int
    scores: dict
    weighted_total: int
    risk_level: str
    explanations: list
    warning_flags: list
    critical_flags: list
    suggested_risk_reserve: Decimal


# ---- Risk signals (for preview / recompute) ----
class RiskSignals(BaseModel):
    category_marker: str | None = None
    stolen_marker: bool = False
    outstanding_finance: bool = False
    write_off_marker: bool = False
    mileage_discrepancy: bool = False
    imported: bool = False
    plate_changes: int = 0
    keeper_changes: int = 0
    mot_fail_count: int = 0
    dangerous_defect_count: int = 0
    major_defect_count: int = 0
    repeated_mot_failures: bool = False
    non_runner: bool = False
    condition_grade: int | None = None
    missing_service_history: bool = False
    one_key_only: bool = False
    unusually_low_market_price: bool = False
    comparable_count: int = 3
    age_years: Decimal | None = None
    mileage: int | None = None


# ---- Appraisal ----
class AppraisalBase(BaseModel):
    expected_retail_price: Decimal | None = Field(default=None, ge=0)
    conservative_retail_price: Decimal | None = Field(default=None, ge=0)
    optimistic_retail_price: Decimal | None = Field(default=None, ge=0)
    expected_negotiated_discount: Decimal = Field(default=Decimal("0"), ge=0)
    pricing_confidence: str = "MEDIUM"
    target_profit: Decimal = Field(default=Decimal("1200"), ge=0)
    risk_reserve: Decimal = Field(default=Decimal("300"), ge=0)
    desired_roi: Decimal = Field(default=Decimal("0.15"), ge=0, le=5)
    estimated_days_to_sell: int = Field(default=45, ge=1, le=365)
    current_bid: Decimal | None = Field(default=None, ge=0)


class AppraisalCreate(AppraisalBase):
    vehicle_id: int
    auction_listing_id: int | None = None
    status: AppraisalStatus = AppraisalStatus.DRAFT
    cost_items: list[CostItemCreate] = Field(default_factory=list)
    comparables: list[ComparableCreate] = Field(default_factory=list)
    risk_signals: RiskSignals | None = None


class AppraisalUpdate(AppraisalBase):
    status: AppraisalStatus | None = None
    cost_items: list[CostItemCreate] | None = None
    comparables: list[ComparableCreate] | None = None
    risk_signals: RiskSignals | None = None


class AppraisalOut(AppraisalBase, ORMModel):
    id: int
    dealership_id: int
    vehicle_id: int
    auction_listing_id: int | None
    appraiser_id: int
    status: str
    recommendation: str | None
    confidence_score: str | None
    safe_max_bid: Decimal | None
    absolute_max_bid: Decimal | None
    break_even_bid: Decimal | None
    expected_profit: Decimal | None
    pessimistic_profit: Decimal | None
    optimistic_profit: Decimal | None
    expected_roi: Decimal | None
    risk_level: str | None
    result_snapshot: dict
    created_at: datetime
    updated_at: datetime
    cost_items: list[CostItemOut] = Field(default_factory=list)
    comparables: list[ComparableOut] = Field(default_factory=list)
    risk_assessment: RiskAssessmentOut | None = None


# ---- Calculation preview (no persistence) ----
class PreviewFeeBand(BaseModel):
    fixed_fee: Decimal = Decimal("0")
    percentage: Decimal = Decimal("0")
    minimum_fee: Decimal | None = None
    maximum_fee: Decimal | None = None
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    vat_applicable: bool = True
    stated_inclusive: bool = False


class PreviewRequest(BaseModel):
    expected_retail_price: Decimal | None = None
    conservative_retail_price: Decimal | None = None
    optimistic_retail_price: Decimal | None = None
    expected_negotiated_discount: Decimal = Decimal("0")
    target_profit: Decimal = Decimal("1200")
    risk_reserve: Decimal = Decimal("300")
    desired_roi: Decimal = Decimal("0.15")
    estimated_days_to_sell: int = 45
    current_bid: Decimal | None = None
    guide_price: Decimal | None = None
    pricing_confidence: str = "MEDIUM"
    cost_items: list[CostItemCreate] = Field(default_factory=list)
    # Fees: either resolve from an auction house, or pass bands inline.
    auction_house_id: int | None = None
    fee_bands: list[PreviewFeeBand] = Field(default_factory=list)
    risk_signals: RiskSignals | None = None


class EvaluationResponse(BaseModel):
    calculation: dict | None
    risk: dict
    recommendation: dict
